from util import generate_random_string, normalize_whitespace
from ios_backup.db import QueryBuilder


def test_content_query_all():
    query = QueryBuilder.content()
    expected_query = """
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1
        """
    assert query.strip() == expected_query.strip()


def test_content_query_domain():
    domain = generate_random_string(10)
    query = QueryBuilder.content(domain)
    expected_query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1 AND domain LIKE '{domain}%'
        """
    assert normalize_whitespace(query) == normalize_whitespace(expected_query)


def test_content_query_namespace():
    namespace = generate_random_string(15)
    query = QueryBuilder.content(namespace)
    expected_query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1 AND domain LIKE '{namespace}%'
        """
    assert normalize_whitespace(query) == normalize_whitespace(expected_query)


def test_content_query_domain_and_namespace():
    domain = generate_random_string(10)
    namespace = generate_random_string(15)
    query = QueryBuilder.content(domain, namespace)
    expected_query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1 AND domain LIKE '{domain}%-{namespace}%'
        """
    assert normalize_whitespace(query) == normalize_whitespace(expected_query)


def test_content_query_path():
    path = generate_random_string(20)
    query = QueryBuilder.content(path_prefix=path)
    expected_query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1 AND relativePath LIKE '{path}%'
        """
    assert normalize_whitespace(query) == normalize_whitespace(expected_query)


def test_content_query_domain_and_namespace_and_path():
    domain = generate_random_string(10)
    namespace = generate_random_string(15)
    path = generate_random_string(20)
    query = QueryBuilder.content(domain, namespace, path)
    expected_query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1 AND domain LIKE '{domain}%-{namespace}%' AND relativePath LIKE '{path}%'
        """
    assert normalize_whitespace(query) == normalize_whitespace(expected_query)
