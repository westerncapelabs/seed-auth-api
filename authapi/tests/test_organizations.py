from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from rest_framework import status

from authapi.serializers import (
    OrganizationSummarySerializer, TeamSummarySerializer,
    UserSummarySerializer, OrganizationSerializer)
from authapi.models import SeedTeam, SeedOrganization
from authapi.tests.base import AuthAPITestCase


class OrganizationTests(AuthAPITestCase):
    def test_get_organization_list(self):
        '''A GET request to the organizations endpoint should return a list
        of organizations.'''
        org1 = SeedOrganization.objects.create()
        org2 = SeedOrganization.objects.create()
        url = reverse('seedorganization-list')
        context = self.get_context(url)

        expected = [
            OrganizationSerializer(instance=o, context=context).data
            for o in [org1, org2]
        ]

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            sorted(expected, key=lambda i: i['id']),
            sorted(response.data, key=lambda i: i['id']))

    def test_get_organization_list_archived(self):
        '''Archived organizations should not appear on the list of
        organizations.'''
        org = SeedOrganization.objects.create(title='test org')

        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 1)

        org.archived = True
        org.save()
        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 0)

    def test_get_organization_list_archived_true_queryparam(self):
        '''If the queryparam archived is true, show only archived
        organizations.'''
        org = SeedOrganization.objects.create(title='test org')

        response = self.client.get(
            '%s?archived=true' % reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 0)

        org.archived = True
        org.save()
        response = self.client.get(
            '%s?archived=true' % reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 1)

    def test_get_organization_list_archived_false_queryparam(self):
        '''If the queryparam archived is false, show only non-archived
        organizations.'''
        org = SeedOrganization.objects.create(title='test org')

        response = self.client.get(
            '%s?archived=false' % reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 1)

        org.archived = True
        org.save()
        response = self.client.get(
            '%s?archived=false' % reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 0)

    def test_get_organization_list_archived_both_queryparam(self):
        '''If the queryparam archived is both, show all organizations.'''
        org1 = SeedOrganization.objects.create(title='test org')
        org1.archived = True
        org1.save()
        SeedOrganization.objects.create(title='test org')

        response = self.client.get(
            '%s?archived=both' % reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 2)

        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data), 1)

    def test_get_organization_list_archived_invalid_queryparam(self):
        '''If the archived querystring parameter is not one of true, false, or
        both, an appropriate error should be returned.'''
        response = self.client.get(
            '%s?archived=foo' % reverse('seedorganization-list'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'archived': ['Must be one of [both, false, true]'],
        })

    def test_get_organization_list_archived_teams(self):
        '''When getting the list of organizations, the archived teams should
        not be visible.'''
        org = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org)

        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data[0]['teams']), 1)

        team.archived = True
        team.save()
        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data[0]['teams']), 0)

    def test_get_organization_list_inactive_users(self):
        '''When getting the list of organizations, the inactive users should
        not be shown in the list of users.'''
        org = SeedOrganization.objects.create(title='test org')
        user = User.objects.create_user('test user')
        org.users.add(user)

        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data[0]['users']), 1)

        user.is_active = False
        user.save()
        response = self.client.get(reverse('seedorganization-list'))
        self.assertEqual(len(response.data[0]['users']), 0)

    def test_create_organization_no_required(self):
        '''If the POST request is missing required field, an error should be
        returned.'''
        response = self.client.post(reverse('seedorganization-list'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'title': ['This field is required.']
        })

    def test_create_organization(self):
        '''A POST request to the organizations endpoint should create a new
        organization.'''
        data = {
            'title': 'test org',
        }
        response = self.client.post(
            reverse('seedorganization-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        [org] = SeedOrganization.objects.all()
        self.assertEqual(org.id, response.data['id'])
        self.assertEqual(org.title, data['title'])

    def test_get_organization(self):
        '''A GET request to an organization's endpoint should return the
        organization's details.'''
        organization = SeedOrganization.objects.create()
        url = reverse('seedorganization-detail', args=[organization.id])
        context = self.get_context(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = OrganizationSerializer(
            instance=organization, context=context)
        self.assertEqual(response.data, expected.data)

    def test_delete_organization(self):
        '''A DELETE request on an organization should archive it.'''
        org = SeedOrganization.objects.create(title='test org')
        self.assertFalse(org.archived)

        response = self.client.delete(
            reverse('seedorganization-detail', args=[org.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        org.refresh_from_db()
        self.assertTrue(org.archived)

    def test_serializer(self):
        '''The organization serializer should return the correct
        information.'''
        organization = SeedOrganization.objects.create(title='testorg')
        user = User.objects.create_user('foo@bar.org')
        organization.users.add(user)
        team = organization.seedteam_set.create()
        url = self.get_full_url(
            'seedorganization-detail', args=[organization.id])
        context = self.get_context(url)

        data = OrganizationSerializer(
            instance=organization, context=context).data
        self.assertEqual(data, {
            'url': url,
            'id': organization.id,
            'users': [
                UserSummarySerializer(instance=user, context=context).data],
            'teams': [
                TeamSummarySerializer(instance=team, context=context).data],
            'archived': organization.archived,
            'title': organization.title,
        })

    def test_summary_serializer(self):
        '''The organization summary serializer should return the correct
        summarized information.'''
        organization = SeedOrganization.objects.create()
        url = self.get_full_url(
            'seedorganization-detail', args=[organization.id])
        context = self.get_context(url)

        data = OrganizationSummarySerializer(
            instance=organization, context=context).data
        self.assertEqual(data, {
            'url': url,
            'id': organization.id,
        })

    def test_add_user_to_organization(self):
        '''Adding a user to an organization should create a relationship
        between the two.'''
        org = SeedOrganization.objects.create(title='test org')
        user = User.objects.create_user(username='test@example.org')
        self.assertEqual(len(org.users.all()), 0)

        response = self.client.post(
            reverse('seedorganization-users-list', args=[org.id]), {
                'user_id': user.id
            })
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        org.refresh_from_db()
        self.assertEqual(len(org.users.all()), 1)

    def test_add_missing_user_to_organization(self):
        '''If a non-existing user is trying to be added to an organization,
        an appropriate error should be returned.'''
        org = SeedOrganization.objects.create(title='test org')

        response = self.client.post(
            reverse('seedorganization-users-list', args=[org.id]), {
                'user_id': 7,
            })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'user_id': ['Invalid pk "7" - object does not exist.']
        })

    def test_remove_user_from_organization(self):
        '''Removing a user from an organization should remove the relationship
        between the two.'''
        org = SeedOrganization.objects.create(title='test org')
        user = User.objects.create_user(username='test@example.org')
        org.users.add(user)
        self.assertEqual(len(org.users.all()), 1)

        response = self.client.delete(
            reverse('seedorganization-users-detail', args=[org.id, user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        org.refresh_from_db()
        self.assertEqual(len(org.users.all()), 0)

    def test_create_team_for_organization(self):
        '''Should create a team and the relation between the team and
        organization.'''
        org = SeedOrganization.objects.create(title='test org')
        data = {
            'title': 'test team',
        }

        response = self.client.post(
            reverse('seedorganization-teams-list', args=[org.id]), data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [team] = SeedTeam.objects.all()
        self.assertEqual(team.organization, org)
        self.assertEqual(team.title, data['title'])

    def test_get_teams_for_organization(self):
        '''Getting a list of teams for an organization should only return that
        organization's teams.'''
        org1 = SeedOrganization.objects.create(title='test org')
        org2 = SeedOrganization.objects.create(title='test org')
        team1 = SeedTeam.objects.create(title='test team', organization=org1)
        SeedTeam.objects.create(title='test team', organization=org2)

        response = self.client.get(
            reverse('seedorganization-teams-list', args=[org1.pk]))
        [team] = response.data

        self.assertEqual(team['id'], team1.id)

    def test_create_permission_for_organizations_team(self):
        '''Should be able to create a permission for an organization's team.'''
        org = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org)
        data = {
            'type': 'foo:bar',
            'object_id': '2',
            'namespace': 'foo',
        }

        self.assertEqual(len(team.permissions.all()), 0)

        self.client.post(
            reverse(
                'seedorganization-teams-permissions-list',
                args=[org.pk, team.pk]
            ),
            data=data)

        self.assertEqual(len(team.permissions.all()), 1)

    def test_remove_permission_for_organizations_team(self):
        '''Should be able to remove a permission for an organization's team.'''
        org = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org)
        permission = team.permissions.create(
            type='foo:bar', object_id='2', namespace='foo')

        self.assertEqual(len(team.permissions.all()), 1)

        self.client.delete(
            reverse(
                'seedorganization-teams-permissions-detail',
                args=[org.pk, team.pk, permission.pk]
            ))

        self.assertEqual(len(team.permissions.all()), 0)

    def test_remove_permission_for_other_organization_team(self):
        '''Should not be able to remove a permission for another
        organization's team.'''
        org1 = SeedOrganization.objects.create(title='test org')
        org2 = SeedOrganization.objects.create(title='test org')
        team1 = SeedTeam.objects.create(title='test team', organization=org1)
        team2 = SeedTeam.objects.create(title='test team', organization=org2)
        permission = team1.permissions.create(
            type='foo:bar', object_id='2', namespace='foo')

        response = self.client.delete(
            reverse(
                'seedorganization-teams-permissions-detail',
                args=[org2.pk, team2.pk, permission.pk]
            ))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_user_to_organizations_team(self):
        '''Should be able to add an existing user to an organization's team.'''
        org = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org)
        user = User.objects.create_user('test user')
        data = {
            'user_id': user.pk,
        }

        response = self.client.post(
            reverse(
                'seedorganization-teams-users-list',
                args=[org.pk, team.pk]),
            data=data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        [teamuser] = team.users.all()
        self.assertEqual(teamuser, user)

    def test_remove_user_from_organizations_team(self):
        '''Should be able to remove an existing user from an organization's
        team.'''
        org = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org)
        user = User.objects.create_user('test user')
        team.users.add(user)

        self.assertEqual(len(team.users.all()), 1)

        response = self.client.delete(
            reverse(
                'seedorganization-teams-users-detail',
                args=[org.pk, team.pk, user.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(team.users.all()), 0)

    def test_remove_user_from_other_organizations_team(self):
        '''Should not be able to remove user's from a team belonging to
        another organization.'''
        org1 = SeedOrganization.objects.create(title='test org')
        org2 = SeedOrganization.objects.create(title='test org')
        team = SeedTeam.objects.create(title='test team', organization=org1)
        user = User.objects.create_user('test user')

        response = self.client.delete(
            reverse(
                'seedorganization-teams-users-detail',
                args=[org2.pk, team.pk, user.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
