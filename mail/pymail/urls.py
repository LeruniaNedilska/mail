from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.start, name='start'),
    url(r'^signin$', views.signin, name='signin'),
    url(r'^signup$', views.signup, name='signup'),
    url(r'^signout$', views.signout, name='signout'),
    url(r'^inbox$', views.template, name='inbox'),
    url(r'^sent$', views.template, name='sent'),
    url(r'^important$', views.template, name='important'),
    url(r'^trash$', views.template, name='trash'),
    url(r'^spam$', views.template, name='spam'),
    url(r'^new$', views.new, name='new'),
    url(r'^reply$', views.handler, name='handler'),
    url(r'^send$', views.send_new_message, name='send_new'),
    url(r'^(?P<category>[a-z]+)/(?P<message_id>[^/]+)/$', views.message, name='see_message'),
    url(r'^search$', views.template, name='search'),
    url(r'^stat/(?P<days>[0-9]+)$', views.stats, name='stats'),
    url(r'^memory$', views.memory_usage, name='memory'),
]
