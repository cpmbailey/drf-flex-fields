import pytest
from django.urls import reverse
from tests.testapp.models import Pet, Person, Company

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        company = Company.objects.create(name='McDonalds')
        person = Person.objects.create(
            name='Fred',
            hobbies='sailing',
            employer=company
        )
        pet = Pet.objects.create(
            name='Garfield',
            toys='paper ball, string',
            species='cat',
            owner=person
        )
        yield
        pet.delete()
        person.delete()
        company.delete()


@pytest.fixture
def pet(db):
    return Pet.objects.get()


def test_retrieve_expand(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    response = client.get(url+'?expand=owner', format='json')

    assert response.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': 1
        }
    }


def test_retrieve_sparse(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    response = client.get(url+'?fields=name,species', format='json')

    assert response.data == {
        'name': 'Garfield',
        'species': 'cat'
    }


def test_retrieve_sparse_whitespace(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    response = client.get(url+'?fields=name, species', format='json')

    assert response.data == {
        'name': 'Garfield',
        'species': 'cat'
    }


def test_retrieve_omit(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    response = client.get(url+'?omit=toys,owner', format='json')

    assert response.data == {
        'name': 'Garfield',
        'species': 'cat'
    }


def test_retrieve_sparse_and_deep_expand(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    url = url + '?fields=owner.employer&expand=owner.employer'
    response = client.get(url, format='json')

    assert response.data == {
        'owner': {
            'employer': {
                'public': False,
                'name': 'McDonalds'
            }
        }
    }


def test_retrieve_omit_and_deep_expand(client, pet):
    url = reverse('pet-detail', args=[pet.id])
    url = url + '?omit=species,toys,owner.employer.public&expand=owner.employer'
    response = client.get(url, format='json')

    assert response.data == {
        'name': 'Garfield',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': {
                'name': 'McDonalds'
            }
        }
    }


@pytest.mark.parametrize('expand', [
    'owner',
    '*',
], ids=('field', 'wildcard'))
def test_list_expand(expand, client):
    url = reverse('pet-list')
    url = url + '?expand=' + expand
    response = client.get(url, format='json')

    assert response.data[0] == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': 1
        }
    }


@pytest.mark.parametrize('expand', [
    'owner.employer',
    'owner.*',
], ids=('field', 'wildcard'))
def test_list_nested_expand(expand, client):
    url = reverse('pet-list')
    url = url + '?expand=' + expand
    response = client.get(url, format='json')

    assert response.data[0] == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': {
                'name': 'McDonalds',
                'public': False
            }
        }
    }
