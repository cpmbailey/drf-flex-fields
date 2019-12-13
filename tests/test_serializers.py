import pytest
from tests.testapp.models import Pet, Person, Company
from tests.testapp.serializers import PetSerializer


class MockRequest:
    def __init__(self, query_params=None, method='GET'):
        self.query_params = query_params or {}
        self.method = method


def test_basic_field_include():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred')
    )

    serializer = PetSerializer(pet, fields=['name', 'toys'])
    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string'
    }


def test_nested_field_include():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', employer=Company(name='McDonalds'))
    )

    serializer = PetSerializer(pet, expand=['owner.employer'], fields=['owner.employer.name'])
    assert serializer.data == {
        'owner': {
            'employer': {
                'name': 'McDonalds'
            }
        }
    }


def test_nested_field_include_all():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', employer=Company(name='McDonalds'))
    )

    serializer = PetSerializer(pet, expand=['owner.employer'], fields=['owner.employer.*'])
    assert serializer.data == {
        'owner': {
            'employer': {
                'name': 'McDonalds',
                'public': False
            }
        }
    }


def test_basic_field_omit():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred')
    )

    serializer = PetSerializer(pet, exclude=['species', 'owner'])
    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string'
    }


def test_nested_field_omit():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', employer=Company(name='McDonalds'))
    )

    serializer = PetSerializer(pet, expand=['owner.employer'], exclude=['species', 'owner.hobbies', 'owner.employer.public'])
    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'owner': {
            'name': 'Fred',
            'employer': {
                'name': 'McDonalds'
            }
        }
    }


def test_expand_from_request():
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', hobbies='sailing', employer=Company(name='McDonalds'))
    )

    request = MockRequest(query_params={'expand': 'owner.employer'})
    serializer = PetSerializer(pet, context={'request': request})

    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': {
                'public': False,
                'name': 'McDonalds'
            }
        }
    }


@pytest.mark.parametrize('expand', [
    'owner',
    '*',
], ids=('field', 'wildcard'))
def test_expand(expand):
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', hobbies='sailing')
    )

    serializer = PetSerializer(pet, expand=[expand])
    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': None
        }
    }


@pytest.mark.parametrize('expand', [
    'owner.employer',
    'owner.*',
], ids=('field', 'wildcard'))
def test_nested_expand(expand):
    pet = Pet(
        name='Garfield',
        toys='paper ball, string',
        species='cat',
        owner=Person(name='Fred', hobbies='sailing', employer=Company(name='McDonalds'))
    )

    serializer = PetSerializer(pet, expand=[expand])
    assert serializer.data == {
        'name': 'Garfield',
        'toys': 'paper ball, string',
        'species': 'cat',
        'owner': {
            'name': 'Fred',
            'hobbies': 'sailing',
            'employer': {
                'public': False,
                'name': 'McDonalds'
            }
        }
    }
