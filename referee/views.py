from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model


class TimePeriodMixin(object):
    '''Will add the currently active time period to the template context
    or False if no active time period.

    Configuration:
      `time_period_model`: The model class that implements TimePeriodBase.
      `queryset`: If not set TimePeriod.current is used

    If the app that implements `TimePeriod` is the same as the one the
    current request is on and that app's urls has `app_name` configured
    in `urls.py` model can be automatically found.
    I.e.: url(r'^test/', include('test_app.urls', namespace='test',
              app_name='test_app')),

    Raises:
      ImproperlyConfigured: If no model has been defined

    '''
    time_period_model = None
    _model = None
    queryset = None

    def get_model(self):
        if self._model: return self._model

        model = self.time_period_model
        if model is None:
            model = get_model(self.request.resolver_match.app_name,
                              'TimePeriod')
            if not model:
                raise ImproperlyConfigured(
                    '`model` is not set for TimePeriod.'
                )

        self._model = model
        return model

    def get_queryset(self):
        if self.queryset is None:
            model = self.get_model()
            return model.current
        else:
            return self.queryset

    def get_time_period(self):
        model = self.get_model()
        queryset = self.get_queryset()

        try:
            return queryset.get()
        except model.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        context = super(TimePeriodMixin, self).get_context_data(**kwargs)
        context['time_period'] = self.get_time_period()

        return context
