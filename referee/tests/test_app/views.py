from django.views.generic import TemplateView

from referee.models import TimePeriod
from referee.views import TimePeriodMixin


class TimePeriodView(TimePeriodMixin, TemplateView):
    model = TimePeriod
    template_name = 'empty.html'
