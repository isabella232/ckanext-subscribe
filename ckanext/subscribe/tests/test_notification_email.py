# encoding: utf-8

import datetime

import pytest
import mock
from lib.helpers import literal

from ckan import model
import ckan.tests.factories as ckan_factories
from ckan.lib.helpers import config

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import dictize_notifications
from ckanext.subscribe.notification_email import (
    send_notification_email,
    get_notification_email_contents,
    get_notification_email_vars,
    dataset_link_from_activity,
    dataset_href_from_activity,
)
from ckanext.subscribe.tests import factories
from ckanext.subscribe.tests import SubscribeBase


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestSendNotificationEmail(SubscribeBase):
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_basic(self, mail_recipient):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        send_notification_email(
            code='the-code', email='bob@example.com',
            notifications=notifications)

        mail_recipient.assert_called_once()
        body = mail_recipient.call_args[1]['body']
        print(body)
        assert dataset['title'] in body
        assert'{}/dataset/{}'.format(config.get('ckan.site_url'), dataset['id']) in body
        assert 'new dataset' in body
        body = mail_recipient.call_args[1]['body_html']
        print(body)
        assert dataset['title'] in body
        assert '{}/dataset/{}'.format(config.get('ckan.site_url'), dataset['id']) in body
        assert 'new dataset' in body


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestGetNotificationEmailContents(SubscribeBase):
    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        get_notification_email_contents(
            code='the-code', email='bob@example.com',
            notifications=notifications)

        # just check there are no exceptions

    def test_org(self):
        org = ckan_factories.Organization()
        subscribe_model.Subscribe.set_emails_last_sent(
            subscribe_model.Frequency.IMMEDIATE.value,
            datetime.datetime.now())
        dataset = ckan_factories.Dataset(owner_org=org['id'])
        activity = model.Session.query(model.Activity) \
            .filter_by(object_id=dataset['id']).first()
        subscription_activities = {
            factories.Subscription(organization_id=org['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email = get_notification_email_contents(
            code='the-code', email='bob@example.com',
            notifications=notifications)
        # Check we link to the dataset, not just the org
        assert '{}/dataset/{}'.format(config.get('ckan.site_url'), dataset['name']) in email[1]
        assert '<a href="{}/dataset/{}">Test Dataset</a>'.format(
            config.get('ckan.site_url'), dataset['name']) in email[2]


@pytest.mark.usefixtures('reset_db', 'with_plugins')
class TestGetNotificationEmailVars(SubscribeBase):
    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        assert email_vars['notifications'] == [{
            'activities': [{
               'activity_type': 'new dataset',
               'dataset_href': '{}/dataset/{}'
               .format(config.get('ckan.site_url'), dataset['name']),
               'dataset_link': literal(
                   '<a href="{}/dataset/{}">{}</a>'
                   .format(config.get('ckan.site_url'), dataset['name'], dataset['title'])),
               'timestamp': activity.timestamp}],
            'object_link': '{}/dataset/{}'.format(config.get('ckan.site_url'), dataset['id']),
            'object_name': dataset['name'],
            'object_title': dataset['title'],
            'object_type': 'dataset'}]

    def test_group(self):
        group, activity = factories.GroupActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(group_id=group['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        assert email_vars['notifications'] == [{
            'activities': [
                {'activity_type': 'new group',
                 'dataset_href': '',
                 'dataset_link': '',
                 'timestamp': activity.timestamp}],
            'object_link': '{}/group/{}'.format(config.get('ckan.site_url'), group['id']),
            'object_name': group['name'],
            'object_title': group['title'],
            'object_type': 'group'}]

    def test_org(self):
        org, activity = factories.OrganizationActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(organization_id=org['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        assert email_vars['notifications'] == [{
            'activities': [{'activity_type': 'new organization',
                            'dataset_href': '',
                            'dataset_link': '',
                            'timestamp': activity.timestamp}],
            'object_link': '{}/organization/{}'.format(config.get('ckan.site_url'), org['id']),
            'object_name': org['name'],
            'object_title': org['title'],
            'object_type': 'organization'}]


# sample "changed package" activity for ckan 2.8
CHANGED_PACKAGE_ACTIVITY = {
    'activity_type': 'changed package',
    'data': {
        'actor': 'admin',
        'package': {
            'author': '',
            'author_email': '',
            'creator_user_id': '6bf6ca45-66c1-48c3-92ae-606dbfd74f3e',
            'extras': [],
            'groups': [],
            'id': '80b00ff0-f755-4ce9-9046-938895722da4',
            'isopen': True,
            'license_id': 'cc-by',
            'license_title': 'Creative Commons Attribution',
            'license_url': 'http://www.opendefinition.org/licenses/cc-by',
            'maintainer': '',
            'maintainer_email': '',
            'metadata_created': '2018-01-02T16:29:09.354482',
            'metadata_modified': '2018-01-02T16:29:44.834676',
            'name': 'stream',
            'notes': '',
            'num_resources': 2,
            'num_tags': 0,
            'organization': {
                'approval_status': 'approved',
                'created': '2017-07-21T10:47:30.290814',
                'description': '',
                'id': 'a2be163e-c3c0-43c0-b361-0752f6d3aa6b',
                'image_url': '',
                'is_organization': True,
                'name': 'cabinet-office',
                'revision_id': '1512649a-f1ca-463b-a72a-2d1959487435',
                'state': 'active',
                'title': 'Cabinet Office',
                'type': 'organization'
            },
            'owner_org': 'a2be163e-c3c0-43c0-b361-0752f6d3aa6b',
            'private': False,
            'relationships_as_object': [],
            'relationships_as_subject': [],
            'resources': [],
            'revision_id': '0defca72-c81d-4f62-a4a1-9fadaa089604',
            'state': 'active',
            'tags': [],
            'title': 'Stream',
            'type': 'dataset',
            'url': '',
            'version': ''
        }
    },
    'id': '79a31a90-16ef-425c-8c38-c76a50f518ea',
    'object_id': '2faae9f6-80e2-4dba-8894-0d81503ae452',
    'revision_id': 'f32cdd68-9e55-4fed-8c57-b088b895c49c',
    'timestamp': '2017-11-17T17:37:46.328411',
    'user_id': '1112c36a-4280-4cd0-81bc-5c82f1d52bdd'
}

CUSTOM_ACTIVITY = {
    'user_id': 'user-id',
    'object_id': 'dataset-id',
    'activity_type': 'changed datastore',
    'data': {
        'resource_id': 'resource-id',
        'pkg_type': 'dataset-type',
        'resource_name': 'june-2018',
        'owner_org': 'organization-id',
        'count': 5,
    }
}


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestDatasetLinkFromActivity(object):

    def test_basic(self):
        assert dataset_link_from_activity(CHANGED_PACKAGE_ACTIVITY) == literal(
            '<a href="{}/dataset/stream">Stream</a>'.format(config.get('ckan.site_url')))

    def test_custom_activity(self):
        # don't want an exception
        assert not dataset_link_from_activity(CUSTOM_ACTIVITY)


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestDatasetHrefFromActivity(object):
    def test_basic(self):
        assert dataset_href_from_activity(CHANGED_PACKAGE_ACTIVITY) == '{}/dataset/stream'.format(
            config.get('ckan.site_url'))
