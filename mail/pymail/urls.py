from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.start, name='start'),
    url(r'^signin$', views.signin, name='signin'),
    url(r'^signup$', views.signup, name='signup'),
    url(r'^signout$', views.signout, name='signout'),
    url(r'^inbox$', views.inbox, name='inbox'),
    url(r'^sent$', views.sent, name='sent'),
    url(r'^important$', views.important, name='important'),
    url(r'^trash$', views.trash, name='trash'),
    url(r'^spam$', views.spam, name='spam'),
    url(r'^new$', views.new, name='new'),
    url(r'^received$', views.received, name='received'),
]
