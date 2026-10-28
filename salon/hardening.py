"""Shared auth limits and bounded, non-personal HTTP telemetry."""
import json
import logging
import time
from datetime import timedelta
from uuid import uuid4
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin


@transaction.atomic
def consume(namespace,identity,limit,seconds):
    from .models import AuthRateBucket
    key=salted_hmac('gentleman.auth.'+namespace,identity,algorithm='sha256').hexdigest()
    now=timezone.now()
    bucket,created=AuthRateBucket.objects.select_for_update().get_or_create(key=key,defaults={'expires_at':now+timedelta(seconds=seconds)})
    if created:
        # Bounded opportunistic retention. Skip counters another worker is
        # currently renewing; the maintenance command clears the rest.
        expired=list(AuthRateBucket.objects.select_for_update(skip_locked=True).filter(expires_at__lte=now).order_by('key').values_list('key',flat=True)[:200])
        if expired:AuthRateBucket.objects.filter(key__in=expired).delete()
    if bucket.expires_at<=now:
        bucket.count=0;bucket.expires_at=now+timedelta(seconds=seconds)
    if bucket.count>=limit:return False,max(1,int((bucket.expires_at-now).total_seconds())+1)
    bucket.count+=1;bucket.save(update_fields=['count','expires_at'])
    return True,0


class AuthThrottleMiddleware(MiddlewareMixin):
    def process_view(self,request,view,args,kwargs):
        name=request.resolver_match.url_name
        if request.method!='POST' or name not in {'login','register','password_reset','password_reset_confirm','activate_walkin'}:return None
        # Trust REMOTE_ADDR only. A proxy must sanitize it at the server boundary;
        # arbitrary X-Forwarded-For cannot evade this limiter.
        address=request.META.get('REMOTE_ADDR','unknown')
        allowed,retry=consume('auth-ip',address,100,900)
        if allowed:
            identity=address
            if name=='login':identity+=':'+request.POST.get('username','').strip().casefold()[:150]
            allowed,retry=consume(name,identity,10,900)
        if not allowed:
            response=render(request,'auth/rate_limited.html',status=429)
            response['Retry-After']=str(retry)
            return response


class SafeLogFormatter(logging.Formatter):
    def format(self,record):
        # Django's default server/error messages may contain raw reset URLs or
        # SQL row details. Expose the class/status, never interpolate the message.
        if record.name=='gentleman.http':return record.getMessage()
        request=getattr(record,'request',None)
        match=getattr(request,'resolver_match',None)
        payload={'event':'framework','level':record.levelname,'logger':record.name,
            'request_id':getattr(request,'request_id',None),'route':getattr(match,'route',None),
            'status':getattr(record,'status_code',None)}
        if record.exc_info:payload['exception_type']=record.exc_info[0].__name__
        return json.dumps(payload,ensure_ascii=False)


class ResponsePolicyMiddleware(MiddlewareMixin):
    def process_request(self,request):
        request.request_id=uuid4().hex
        request.started_at=time.perf_counter()

    def process_response(self,request,response):
        response['X-Request-ID']=request.request_id
        response['Referrer-Policy']='same-origin'
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['Content-Security-Policy']=("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if not request.path.startswith('/static/'):
            response['Cache-Control']='private, no-store, max-age=0'
            match=getattr(request,'resolver_match',None)
            logging.getLogger('gentleman.http').info(json.dumps({'event':'http_request','entry_point':'web',
                'request_id':request.request_id,'method':request.method,'route':getattr(match,'route','<unmatched>'),
                'status':response.status_code,'duration_ms':round((time.perf_counter()-request.started_at)*1000,2)}))
        return response
