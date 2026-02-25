# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C) 2022-2025 Albert Engstfeld
#        Copyright (C) 2022      Johannes Hermann
#        Copyright (C) 2022      Julian Rüth
#        Copyright (C) 2022      Nicolas Hörmann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ********************************************************************

import re

# Check that we are on the main branch
branch=$(git branch --show-current)
if branch.strip() != "main":
  raise Exception("You must be on the main branch to release.")
# and that it is up to date with origin/main
git fetch https://github.com/echemdb/electrochemistry-data.git
git reset FETCH_HEAD
git diff --exit-code
git diff --cached --exit-code

$PROJECT = 'electrochemistry-data'

from rever.activities.command import command

command('pixi', 'pixi install --manifest-path "$PWD/pyproject.toml" -e dev')

command('build', 'python -m build')
command('twine', 'twine upload dist/echemdb_ecdata-' + $VERSION + '.tar.gz dist/echemdb_ecdata-' + $VERSION + '-py3-none-any.whl')

$ACTIVITIES = [
    'version_bump',
    'pixi',
    'changelog',
    'tag',
    'push_tag',
    'build',
    'twine',
    'ghrelease',
]

$VERSION_BUMP_PATTERNS = [
    ('pyproject.toml', r'version =', 'version = "$VERSION"'),
    ('echemdb_ecdata/url.py', re.escape(r'def get_echemdb_database_url(version="'), r'def get_echemdb_database_url(version="$VERSION"):'),
    ('echemdb_ecdata/url.py', re.escape(r'        >>> get_echemdb_database_url(version="'), r'        >>> get_echemdb_database_url(version="$VERSION")'),
    ('echemdb_ecdata/url.py', re.escape(r"        'https://github.com/echemdb/electrochemistry-data/releases/download/"), r"        'https://github.com/echemdb/electrochemistry-data/releases/download/$VERSION/data-$VERSION.zip'")
]

$CHANGELOG_FILENAME = 'ChangeLog'
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'
$CHANGELOG_NEWS = 'doc/news'
$PUSH_TAG_REMOTE = 'git@github.com:echemdb/electrochemistry-data.git'

$GITHUB_ORG = 'echemdb'
$GITHUB_REPO = 'electrochemistry-data'

$CHANGELOG_CATEGORIES = ('Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Performance')
