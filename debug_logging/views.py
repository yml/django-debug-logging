from datetime import datetime

from django.conf import settings
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import simplejson

from debug_logging.forms import DateRangeForm
from debug_logging.models import DebugLogRecord, TestRun
from debug_logging.utils import get_project_name, get_hostname, get_revision

RECORDS_PER_PAGE = 50


def index(request):
    runs = TestRun.objects.all()
    
    return render_to_response("debug_logging/index.html", {
        'runs': runs,
    }, context_instance=RequestContext(request))


def run_detail(request):
    from_date = DateRangeForm.DEFAULT_FROM_DATE
    to_date = DateRangeForm.DEFAULT_TO_DATE
    sort = None
    if request.GET:
        form = DateRangeForm(data=request.GET)
        if form.is_valid():
            if form.cleaned_data.get('from_date'):
                from_date = form.cleaned_data['from_date']
            if form.cleaned_data.get('to_date'):
                to_date = form.cleaned_data['to_date']
        
        sort = request.GET.get('sort')
    else:
        form = DateRangeForm()
    
    if sort == 'response_time':
        order_by = '-timer_total'
    elif sort == 'sql_queries':
        order_by = '-sql_num_queries'
    elif sort == 'sql_time':
        order_by = '-sql_time'
    else:
        order_by = '-timestamp'
    
    records = DebugLogRecord.objects.filter(
        timestamp__gte=from_date,
        timestamp__lte=to_date,
    ).order_by(order_by)
    
    aggregates = records.aggregate(
        Avg('timer_total'),
        Avg('timer_cputime'),
        Avg('sql_time'),
        Avg('sql_num_queries'),
        Max('sql_num_queries'),
    )
    
    p = Paginator(records, RECORDS_PER_PAGE)
    try:
        page_num = int(request.GET.get('p', 1))
    except ValueError:
        page_num = 1
    page = p.page(page_num)
    
    return render_to_response("debug_logging/run_detail.html", {
        'form': form,
        'page': page,
        'from_date': from_date,
        'to_date': to_date,
        'aggregates': aggregates,
    }, context_instance=RequestContext(request))


def record_detail(request, record_id):
    record = get_object_or_404(DebugLogRecord, pk=record_id)
    return render_to_response("debug_logging/record_detail.html", {
        'record': record,
    }, context_instance=RequestContext(request))


def start_run(request):
    details = {}
    panels = settings.DEBUG_TOOLBAR_PANELS
    if 'debug_logging.panels.identity.IdentityLoggingPanel' in panels:
        details['project_name'] = get_project_name()
        details['hostname'] = get_hostname()
    if 'debug_logging.panels.revision.RevisionLoggingPanel' in panels:
        details['revision'] = get_revision()
    
    details['start'] = datetime.now()
    
    test_run = TestRun(**details)
    test_run.save()
    
    json_data = simplejson.dumps(test_run, cls=DjangoJSONEncoder)
    return HttpResponse(json_data, content_type='application/json')
