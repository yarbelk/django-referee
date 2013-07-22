from django.contrib import admin

from .models import TimePeriod


class TimePeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'period_start', 'period_end',)


admin.site.register(TimePeriod, TimePeriodAdmin)
