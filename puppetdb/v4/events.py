#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2013 Arcus, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
events.py: A bunch of API methods for interacting with v4 events in the PuppetDB API.

Operators
See the Operators page for the full list of available operators. Note that inequality operators (<, >, <=, >=) are only supported against the timestamp FIELD.

Fields
FIELD may be any of the following. Unless otherwise noted, all fields support both equality and regular expression match operators, but do not support inequality operators.

certname: the name of the node that the event occurred on.
report: the id of the report that the event occurred in; these ids can be acquired via event queries or via the /reports query endpoint.
status: the status of the event; legal values are success, failure, noop, and skipped.
timestamp: the timestamp (from the puppet agent) at which the event occurred. This field supports the inequality operators. All values should be specified as ISO-8601 compatible date/time strings.
run-start-time: the timestamp (from the puppet agent) at which the puppet run began. This field supports the inequality operators. All values should be specified as ISO-8601 compatible date/time strings.
run-end-time: the timestamp (from the puppet agent) at which the puppet run finished. This field supports the inequality operators. All values should be specified as ISO-8601 compatible date/time strings.
report-receive-time: the timestamp (from the PuppetDB server) at which the puppet report was received. This field supports the inequality operators. All values should be specified as ISO-8601 compatible date/time strings.
resource-type: the type of resource that the event occurred on; e.g., File, Package, etc.
resource-title: the title of the resource that the event occurred on
property: the property/parameter of the resource that the event occurred on; e.g., for a Package resource, this field might have a value of ensure. NOTE: this field may contain NULL values; see notes below.
new-value: the new value that Puppet was attempting to set for the specified resource property. NOTE: this field may contain NULL values; see notes below.
old-value: the previous value of the resource property, which Puppet was attempting to change. NOTE: this field may contain NULL values; see notes below.
message: a description (supplied by the resource provider) of what happened during the event. NOTE: this field may contain NULL values; see notes below.
file: the manifest file in which the resource definition is located. NOTE: this field may contain NULL values; see notes below.
line: the line (of the containing manifest file) at which the resource definition can be found. NOTE: this field may contain NULL values; see notes below.
containing-class: the Puppet class where this resource is declared. NOTE: this field may contain NULL values; see notes below.
latest-report?: whether the event occurred in the most recent Puppet run (per-node). NOTE: the value of this field is always boolean (true or false without quotes), and it is not supported by the regex match operator.

Notes on fields that allow NULL values
In the case of a skipped resource event, some of the fields of an event may not have values. We handle this case in a slightly special way when these fields are used in equality (=) or inequality (!=) queries; specifically, an equality query will always return false for an event with no value for the field, and an inequality query will always return true.

The response is a JSON array of events that matched the input parameters. The events are sorted by their timestamps, in descending order:

[
  {
    "certname": "foo.localdomain",
    "old-value": "absent",
    "property": "ensure",
    "timestamp": "2012-10-30T19:01:05.000Z",
    "resource-type": "File",
    "resource-title": "/tmp/reportingfoo",
    "new-value": "file",
    "message": "defined content as '{md5}49f68a5c8493ec2c0bf489821c21fc3b'",
    "report": "38ff2aef3ffb7800fe85b322280ade2b867c8d27",
    "status": "success",
    "file": "/home/user/path/to/manifest.pp",
    "line": 6,
    "containment-path": [ "Stage[main]", "Foo", "File[/tmp/reportingfoo]" ],
    "containing-class": "Foo",
    "run-start-time": "2012-10-30T19:00:00.000Z",
    "run-end-time": "2012-10-30T19:05:00.000Z",
    "report-receive-time": "2012-10-30T19:06:00.000Z"
  },
  {
    "certname": "foo.localdomain",
    "old-value": "absent",
    "property": "message",
    "timestamp": "2012-10-30T19:01:05.000Z",
    "resource-type": "Notify",
    "resource-title": "notify, yo",
    "new-value": "notify, yo",
    "message": "defined 'message' as 'notify, yo'",
    "report": "38ff2aef3ffb7800fe85b322280ade2b867c8d27",
    "status": "success",
    "file": "/home/user/path/to/manifest.pp",
    "line": 10,
    "containment-path": [ "Stage[main]", "", "Node[default]", "Notify[notify, yo]" ],
    "containing-class": null,
    "run-start-time": "2012-10-30T19:00:00.000Z",
    "run-end-time": "2012-10-30T19:05:00.000Z",
    "report-receive-time": "2012-10-30T19:06:00.000Z"
  }
]

"""

__author__ = "monkee"
__version__ = "1.0.1"
__maintainer__ = "monk-ee"
__email__ = "magic.monkee.magic@gmail.com"
__status__ = "Development"

from puppetdb import utils

API_VERSION = 'v3'

def get_events(api_url=None, query='', verify=False, cert=list()):
    """
    Returns events

    :param api_url: Base PuppetDB API url
    :param query: Required. A JSON array of query predicates, in prefix form (the standard ["<OPERATOR>", "<FIELD>", "<VALUE>"] format), conforming to the format described below.
                    The query parameter is described by the following grammar:

                    query: [ {bool} {query}+ ] | [ "not" {query} ] | [ {match} {field} {value} ] | [ {inequality} {field} {value} ]
                    field:          FIELD (conforming to [Fields](#fields) specification below)
                    value:          string
                    bool:           "or" | "and"
                    match:          "=" | "~"
                    inequality:     ">" | ">=" | "<" | "<="
                    For example, for all events in the report with hash ‘38ff2aef3ffb7800fe85b322280ade2b867c8d27’, the JSON query structure would be:

                    ["=", "report", "38ff2aef3ffb7800fe85b322280ade2b867c8d27"]
                    To retrieve all of the events within a given time period:

                    ["and", ["<", "timestamp", "2011-01-01T12:01:00-03:00"],
                            [">", "timestamp", "2011-01-01T12:00:00-03:00"]]
                    To retrieve all of the ‘failure’ events for nodes named ‘foo.*’ and resources of type ‘Service’:

                    ["and", ["=", "status", "failure"],
                            ["~", "certname", "^foo\\."],
                            ["=", "resource-type", "Service"]]
                    To retrieve latest events that are tied to the class found in your update.pp file

                    ["and", ["=", "latest-report?", true],
                            ["~", "file", "update.pp"]]


    """
    return utils._make_api_request(api_url, '/events', verify, cert, params={'query': query})
