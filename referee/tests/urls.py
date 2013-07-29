"""URLs to run the tests."""
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin


from test_app.views import TimePeriodView

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^timeperiod/$', TimePeriodView.as_view(), name='time-period'),
    url(r'^admin/', include(admin.site.urls)),
)
