from django.core.exceptions import ImproperlyConfigured


class TimePeriodMixin(object):
    '''Will add the currently active time period to the template context
    or False if no active time period.

    Configuration:
      `model`: The model class that implements TimePeriodBase. Required.
      `queryset`: If not set TimePeriod.current is used

    Raises:
      ImproperlyConfigured: If no model has been defined
    '''
    model = None
    queryset = None

    def get_model(self):
        if self.model is None:
            raise ImproperlyConfigured('`model` is not set for TimePeriod. ')

        return self.model

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
