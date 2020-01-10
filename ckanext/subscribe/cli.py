import sys
import datetime
import time

import ckan.lib.cli as cli
import ckan.plugins as p


class subscribeCommand(cli.CkanCommand):
    '''subscribe commands

    Usage:

        subscribe initdb
            Initialize the the ckanext-subscribe's database table

        subscribe send-any-notifications [-r] [-i
            Check for activity and for any subscribers, send emails with the
            notifications.
            Option:
              -r --repeatedly - does it repeatedly every 10s

        subscribe create-test-activity {package-name|group-name|org-name}
            Create some activity for testing purposes, for a given existing
            object.

        subscribe delete-test-activity
            Delete any test activity (i.e. clean up after doing
            'create-test-activity'). Works for test activity on all objects.

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    def __init__(self, name):
        self.parser.add_option('-r', '--repeatedly', dest='repeatedly',
                               action='store_true', default=False,
                               help='Repeat every 10s')
        super(subscribeCommand, self).__init__(name)

    def command(self):
        if not self.args:
            print(self.usage)
            sys.exit(1)
        if self.options.repeatedly:
            assert self.args[0] == 'send-any-notifications'
        if self.args[0] == 'initdb':
            self._load_config()
            self._initdb()
        elif self.args[0] == 'send-any-notifications':
            self._load_config()
            self._send_any_notifications()
        elif self.args[0] == 'create-test-activity':
            self._load_config()
            object_id = self.args[1]
            self._create_test_activity(object_id)
        elif self.args[0] == 'delete-test-activity':
            self._load_config()
            self._delete_test_activity()
        else:
            self.parser.error('Unrecognized command')

    def _initdb(self):
        from ckanext.subscribe.model import setup as db_setup
        db_setup()

        print('DB tables created')

    def _send_any_notifications(self):
        log = __import__('logging').getLogger(__name__)
        from ckanext.subscribe import notification
        notification.do_immediate_notifications()
        if self.options.repeatedly:
            while True:
                log.debug('Repeating in 10s')
                time.sleep(10)
                notification.do_immediate_notifications()

    def _create_test_activity(self, object_id):
        from ckan import model
        from ckanext.subscribe import notification
        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            model.repo.new_revision()
        obj = model.Package.get(object_id) or model.Group.get(object_id)
        assert obj, 'Object could not be found'
        grace = notification.get_config('immediate_notification_grace_period')
        site_user = p.toolkit.get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        site_user_obj = model.User.get(site_user['name'])
        activity = model.Activity(
            user_id=site_user_obj.id,
            object_id=obj.id,
            activity_type='test activity',
            revision_id=None,
        )
        # put it slightly in the past, so it notifies immediately
        activity.timestamp = datetime.datetime.now() - grace
        model.Session.add(activity)
        print(activity)
        model.Session.commit()

    def _delete_test_activity(self):
        from ckan import model
        test_activity = model.Session.query(model.Activity) \
            .filter_by(activity_type='test activity') \
            .all()
        for activity in test_activity:
            model.Session.delete(activity)
