"""
Test runner for the JSON Schema official test suite

Tests comprehensive correctness of each draft's validator.

Thank you https://github.com/json-schema/JSON-Schema-Test-Suite for all the work in this file.
"""
from __future__ import print_function

import glob
import json
import itertools
import os
import re
import sys

try:
    from sys import pypy_version_info
except ImportError:
    pypy_version_info = None

if sys.maxunicode == 2 ** 16 - 1:          # This is a narrow build.
    def narrow_unicode_build(case, test):
        if "supplementary Unicode" in test["description"]:
            return "Not running surrogate Unicode case, this Python is narrow."
else:
    def narrow_unicode_build(case, test):  # This isn't, skip nothing.
        return


PY3 = sys.version_info[0] == 3

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
SUITE = os.getenv("JSON_SCHEMA_TEST_SUITE", os.path.join(REPO_ROOT, "JSON-Schema-Test-Suite"))
TESTS_DIR = os.path.join(SUITE, "tests")


import unittest
import mock
import subprocess


JSONSCHEMA_SUITE = os.path.join(SUITE, "bin", "jsonschema_suite")
try:
    remotes_stdout = subprocess.check_output(
        ["python", JSONSCHEMA_SUITE, "remotes"]
    )
except subprocess.CalledProcessError as exc:
    print(exc)
    print(
        'One reason for the error might be that you have to download '
        'JSON-Schema-Test-Suite first:\n\n'
        'git clone git@github.com:json-schema/JSON-Schema-Test-Suite.git --depth=1\n'
    )
    sys.exit(1)
if PY3:
    remotes_stdout = remotes_stdout.decode('utf8')
REMOTES = json.loads(remotes_stdout)


from validictory import validate, FieldValidationError
from validictory.preprocess_ref import preprocess_ref


def make_case(schema, data, valid, name):
    if valid:
        def test_case(self):
            # kwargs = getattr(self, "validator_kwargs", {})
            schema2 = preprocess_ref(schema)
            print('data', data)
            print('schema', schema)
            print("should be valid")
            validate(data, schema2, required_by_default=False)
            # , cls=self.validator_class, **kwargs)
    else:
        def test_case(self):
            # kwargs = getattr(self, "validator_kwargs", {})
            print('data', data)
            print('schema', schema)
            print("should be invalid")
            with self.assertRaises(FieldValidationError):
                schema2 = preprocess_ref(schema)
                validate(data, schema2, required_by_default=False)
                # , cls=self.validator_class, **kwargs)
    if not PY3:
        name = name.encode("utf-8")
    test_case.__name__ = name
    return test_case


def maybe_skip(skip, test_case, case, test):
    if skip is not None:
        reason = skip(case, test)
        if reason is not None:
            test_case = unittest.skip(reason)(test_case)
    return test_case


def mock_get_ref_definition(schema, matched_value):
    print('schema', schema)
    print('matched_value', matched_value)
    print('known_remotes', REMOTES.keys())
    _, _, reference = matched_value.partition("http://localhost:1234/")
    print('reference', reference)
    return mock.Mock(return_value=REMOTES.get(reference))


class TestDraft4RemoteResolution(unittest.TestCase):
    def setUp(self):
        patch = mock.patch("validictory.preprocess_ref.get_ref_definition")
        mo = patch.start()
        mo.side_effect = mock_get_ref_definition
        self.addCleanup(patch.stop)


def define_one_test_class(filename):
    skip = narrow_unicode_build
    fn_identifier, _ = os.path.splitext(os.path.basename(filename))
    test_cls_name = 'TestDraft4{}'.format(fn_identifier.capitalize())
    print('Defining {}...'.format(test_cls_name))
    BaseCls = special_cases.get(fn_identifier, unittest.TestCase)

    with open(filename) as test_file:
        file_content = json.load(test_file)
    test_id = itertools.count(1)
    tests_list = []
    for case in file_content:
        for test in case["tests"]:
            name = "test_%s_%s_%s" % (
                fn_identifier,
                next(test_id),
                re.sub(r"[\W ]+", "_", test["description"]),
            )
            test_case = make_case(
                data=test["data"],
                schema=case["schema"],
                valid=test["valid"],
                name=name,
            )
            test_case = maybe_skip(skip, test_case, case, test)
            tests_list.append((name, test_case))

    class Cls(BaseCls):
        pass
    for name, test in tests_list:
        setattr(Cls, name, test)
    Cls.__name__ = test_cls_name
    globals()[test_cls_name] = Cls


special_cases = {
    'refRemote': TestDraft4RemoteResolution,
}
for filename in glob.iglob(os.path.join(TESTS_DIR, 'draft4/*.json')):
    define_one_test_class(filename)


if __name__ == '__main__':
    try:
        import pytest
        pytest.main([__file__])
    except ImportError:
        unittest.main()
