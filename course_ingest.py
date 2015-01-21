#!/usr/bin/env/python

"""
    course_ingest.py: Given course and section data from the Office of the
    University Registrar (from the Enterprise Data Warehouse), add courses
    as necessary, and course sections of courses.  Links courses to instructors
    vis teacher roles, create a course web site object for each course.  Link
    Sections (instances of courses) to course, instructor (via teacher role)
    and to academic term.

    Exceptions are thrown, caught and logged for missing academic term and
    missing instructor.

    See CHANGELOG.md for history

    To Do:
    --  Create a test file with various test conditions and notes
    --  Move to an update design
    --  Use rdflib
    --  Support Simple VIVO processing
    --  Use argparse to handle command line arguments

    Long Term:
    --  Retire the two phase process where course ingest writes records for
        person ingest, person ingest runs and then course ingest is run again.
        Use add_person to add instructors if needed
    --  Update to VIVO-ISF
"""

__author__ = "Michael Conlon"
__copyright__ = "Copyright 2014, University of Florida"
__license__ = "BSD 3-Clause license"
__version__ = "0.7"

from vivopeople import make_ufid_dictionary
from vivocourses import prepare_teaching_data
from vivocourses import make_term_dictionary
from vivocourses import make_course_dictionary
from vivocourses import make_section_dictionary
from vivocourses import make_course_rdf
from vivocourses import make_section_rdf
from vivofoundation import rdf_header
from vivofoundation import rdf_footer
import vivofoundation as vt
from datetime import datetime
import codecs
import argparse

action_report = {}  # determine the action to be taken for each UFID

# Driver program starts here

parser = argparse.ArgumentParser()
parser.add_argument("filename", help="name of file containing course data to be added to VIVO",
                    default="course", nargs='?')
args = parser.parse_args()

debug = False
sample = 1.0  # Fraction of records to be processed.  Set to 1.0 to process all

file_name = args.filename
add_file = codecs.open(file_name+"_add.rdf", mode='w', encoding='ascii',
                       errors='xmlcharrefreplace')
pos_file = codecs.open(file_name+"_pos.txt", mode='w', encoding='ascii',
                       errors='xmlcharrefreplace')
log_file = codecs.open(file_name+"_log.txt", mode='w', encoding='ascii',
                       errors='xmlcharrefreplace')
exc_file = codecs.open(file_name+"_exc.txt", mode='w', encoding='ascii',
                       errors='xmlcharrefreplace')
add_ufid = {}

print >>add_file, rdf_header()
print >>log_file, datetime.now(), "Course ingest. Version", __version__,\
    "VIVO Tools", vt.__version__
print >>log_file, datetime.now(), "Make UF Taught Dictionary"
teaching_data = prepare_teaching_data(filename='course_data.csv', debug=debug)
print >>log_file, datetime.now(), "Taught dictionary has ",\
    len(teaching_data), " entries"
print >>log_file, datetime.now(), "Make VIVO Term Dictionary"
term_dictionary = make_term_dictionary(debug=debug)
print >>log_file, datetime.now(), "VIVO Term dictionary has ",\
    len(term_dictionary), " entries"
print >>log_file, datetime.now(), "Make VIVO Course Dictionary"
course_dictionary = make_course_dictionary(debug=debug)
print >>log_file, datetime.now(), "VIVO Course dictionary has ",\
    len(course_dictionary), " entries"
print >>log_file, datetime.now(), "Make VIVO Section Dictionary"
section_dictionary = make_section_dictionary(debug=debug)
print >>log_file, datetime.now(), "VIVO Section dictionary has ",\
    len(section_dictionary), " entries"
print >>log_file, datetime.now(), "Make VIVO UFID Dictionary"
ufid_dictionary = make_ufid_dictionary(debug=debug)
print >>log_file, datetime.now(), "VIVO UFID dictionary has ",\
    len(ufid_dictionary), " entries"

# Loop through the course data.  Process each row

print >>log_file, datetime.now(), "Begin Processing"
for teaching_record in teaching_data.values():

    ardf = ""

    # Look for the instructor.  If not found, write to exception log

    try:
        person_uri = ufid_dictionary[teaching_record['ufid']]
        teaching_record['person_uri'] = person_uri
    except KeyError:
        print >>exc_file, "No such instructor on row", teaching_record, "UFID = ", \
            teaching_record['ufid']
        add_ufid[teaching_record['ufid']] = True

        continue

    # Look for the term.  If not found, write to exception log

    try:
        term_uri = term_dictionary[teaching_record['term_name']]
        teaching_record['term_uri'] = term_uri
    except KeyError:
        print >>exc_file, "No such term on row", teaching_record, "Term = ",\
            teaching_record['term_name']
        continue

    # Look for the course.  If not found, add it

    try:
        course_uri = course_dictionary[teaching_record['course_number']]
        teaching_record['course_new'] = False
    except KeyError:
        [add, course_uri] = make_course_rdf(teaching_record)
        ardf = ardf + add
        print >>log_file, "Add course", teaching_record['course_name'],\
            "at", course_uri
        course_dictionary[teaching_record['course_number']] = course_uri
        teaching_record['course_new'] = True
    teaching_record['course_uri'] = course_uri

    # Look for the section.  If not found, add it

    try:
        section_uri = section_dictionary[teaching_record['section_name']]
    except KeyError:
        [add, section_uri] = make_section_rdf(teaching_record)
        print >>log_file, "Add section", teaching_record['section_name'],\
            "at", section_uri
        ardf = ardf + add
        section_dictionary[teaching_record['section_name']] = section_uri

    teaching_record['section_uri'] = section_uri

    if ardf != "":
        add_file.write(ardf)

#   Done processing the courses.  Wrap-up

for ufid in sorted(add_ufid.keys()):

    # Write records into a position file.  Records have the UFID to be
    # added to VIVO, along with a zero in the HR_POSITION field (last
    # field) indicating to person_ingest that no position should be created
    # for the UFID being added.

    print >>pos_file, "NULL" + "|" + ufid + "|" + \
        "NULL" + "|" + "NULL" + "|" + "NULL" + "|" + "NULL" + "|" + \
        "NULL" + "|" + "0"

print >>add_file, rdf_footer()
print >>log_file, datetime.now(), "End Processing"

add_file.close()
log_file.close()
exc_file.close()
pos_file.close()
