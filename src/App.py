"""
App.py
---
SelahSearch
RESTful service API which uses NLP to match worship lyrics with bible references

"""

# You can import more modules from the standard library here if you need them
# (which you will, e.g. sqlite3).
import os
from pathlib import Path

# You can import more third-party packages here if you need them, provided
# that they've been used in the weekly labs, or specified in this assignment,
# and their versions match.
from dotenv import load_dotenv          # Needed to load the environment variables from the .env file
import google.generativeai as genai     # Needed to access the Generative AI API

# Other modules
import requests
from flask import Flask, send_file
from flask_restx import Resource, Api
from flask_restx import fields
from flask_restx import reqparse

import pandas as pd
import sqlite3
from datetime import datetime

# Constants and OS
curr_dir = os.path.dirname(os.path.abspath(__file__))
studentid = Path(__file__).stem         # Will capture your zID from the filename.
db_file = f"{studentid}.db"           # Use this variable when referencing the SQLite database file.
txt_file = f"{studentid}.txt"          # Use this variable when referencing the txt file for Q7.
table_name = "stops"

HOSTNAME = "127.0.0.1"
PORT = 5000


# Load the environment variables from the .env file
load_dotenv()

# Configure the API key
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Create a Gemini Pro model
gemini = genai.GenerativeModel('gemini-pro')


# App
app = Flask(__name__)
api = Api(app,
          default="RESTful API for Deutsche Bahn",
          title="RESTful API for Deutsche Bahn",
          description="A service to explore how RESTful APIs can enhance experience of passengers around Germany.")


# Schemas
link_model = api.model('Link', {
    'href': fields.String
})

links_model = api.model('Links', {
    'self': fields.Nested(link_model),
    'next': fields.Nested(link_model),
    'prev': fields.Nested(link_model),
})

stop_model = api.model('Stop', {
    'last_updated': fields.DateTime(
        dt_format="%Y-%m-%d-%H:%M:%S",
        description="The datetime of most recent update",
        example="2020-06-23-12:54:38"
    ),
    'name': fields.String(
        description='The name of the stop',
        example="Leipzig"
    ),
    'latitude': fields.Float(
        description='The latitude of the stop location',
        example=-15.29610
    ),
    'longitude': fields.Float(
        description='The longitude of the stop location',
        example=-34.15608
    ),
    'next_departure': fields.String(
        description="The platform and direction of next departure from this stop",
        example="Platform 4 towards Leipzig"
    )
})

permitted_cols = [
    "last_updated",
    "name",
    "latitude",
    "longitude",
    "next_departure"
]


# Parsers
addParser = reqparse.RequestParser(bundle_errors=True)
addParser.add_argument('query', required=True, type=str)

getParser = reqparse.RequestParser(bundle_errors=True)
getParser.add_argument('include', action='split', required=False, type=str)

putParser = reqparse.RequestParser(bundle_errors=True)
putParser.add_argument('name', required=False, type=str)
putParser.add_argument('last_updated', required=False, type=str)
putParser.add_argument('latitude', required=False, type=float)
putParser.add_argument('longitude', required=False, type=float)
putParser.add_argument('next_departure', required=False, type=str)


# Routes and HTTP methods
@api.route('/stops')
class Stops(Resource):
    @api.response(400, 'Validation Error')
    @api.response(503, 'Bad Gateway Error')
    @api.response(200, 'Update Successful')
    @api.response(201, 'Create Successful')
    @api.expect(addParser, validate=True)
    @api.param('query', description='The query string used to add stops',
               example="halle")
    @api.doc(description="Add/update stops that match a query string")
    def put(self):
        args = addParser.parse_args()
        query = args.get('query')
        queryData = requestStops(query)
        if not queryData:
            api.abort(404, f"No results found for query {query}", query=query)

        for i in range(len(queryData)):
            queryData[i]['id'] = int(queryData[i]['id'])
            curr_id = queryData[i]['id']

            location = queryData[i]['location']
            queryData[i]['latitude'] = location['latitude']
            queryData[i]['longitude'] = location['longitude']
            queryData[i].pop('location')

            queryData[i].pop('products')

            queryData[i]['last_updated'] = datetime.now().replace(microsecond=0).strftime("%Y-%m-%d-%H:%M:%S")

            next_dep = requestNextDeparture(curr_id)
            if next_dep:
                queryData[i]['next_departure'] = next_dep
            else:
                queryData[i]['next_departure'] = ""

            # get link for self only
            link = f"http://{HOSTNAME}:{PORT}/stops/{curr_id}"
            queryData[i]['_links_self'] = link

        columns = list(queryData[0].keys())
        df = pd.DataFrame(queryData, columns=columns)

        output, code = createSQLDatabase(df, queryData, db_file, table_name)
        if code not in [200, 201]:
            return output, code

        output = []
        for q in queryData:
            links = {
                'self': {
                    'href': q['_links_self']
                }
            }
            output.append({
                'stop_id': q['id'],
                'last_updated': q['last_updated'],
                '_links': links
            })
        return output, code


@api.route('/stops/<int:id>')
@api.param('id', description='The Stop identifier', example=1234567)
class Stop(Resource):
    @api.response(404, 'Stop not found')
    @api.response(503, 'Bad Gateway Error')
    @api.response(400, 'Validation Error')
    @api.response(200, 'Successful')
    @api.expect(getParser, validate=True)
    @api.param('include', description='Comma separated fields to include for stop',
               example="name,last_updated")
    @api.doc(description="Get a stop by its ID")
    def get(self, id):
        # handle include args
        args = getParser.parse_args()
        include = args.get('include')

        if include is not None:
            include_str = ','.join(include)
            # verify cols
            for c in include:
                if c is None or c == "":
                    api.abort(400, "Include parameter cannot be blank: ''", stop_id=id, include=include_str)
                if c not in permitted_cols:
                    api.abort(400, f"Parameter '{c}' not permitted", stop_id=id, include=include_str)

            df = querySQLDatabase(db_file, f'SELECT id,{include_str} FROM "{table_name}" WHERE id = "{id}"')
        else:
            df = querySQLDatabase(db_file, f'SELECT * FROM "{table_name}" WHERE id = "{id}"')

        if id not in list(df['id']):
            api.abort(404, f"The stop_id {id} was not found in the database.", stop_id=id)

        stop = df.to_dict('records')[0]

        # get links
        links = getAdjLinks(db_file, id)

        if include is not None:
            return_stop = {
                "stop_id": id
            }
            for c in include:
                return_stop[c] = stop[c]
            return_stop['_links'] = links
            return return_stop, 200

        # return everything if include argument not given
        return {
            "stop_id": id,
            "last_updated": stop['last_updated'],
            "name": stop['name'],
            "latitude": stop['latitude'],
            "longitude": stop['longitude'],
            "next_departure": stop['next_departure'],
            '_links': links
        }, 200

    @api.response(404, 'Stop not found')
    @api.response(503, 'Bad Gateway Error')
    @api.response(200, 'Successful')
    @api.doc(description="Delete a stop by its ID")
    def delete(self, id):
        df = querySQLDatabase(db_file, f'SELECT * FROM "{table_name}" WHERE id = "{id}"')

        if id not in list(df['id']):
            api.abort(404, f"The stop_id {id} was not found in the database.", stop_id=id)

        # SQLite delete
        cnx = sqlite3.connect(db_file)
        cur = cnx.cursor()
        try:
            deleteValues(cnx, cur, table_name, id)
        except sqlite3.Error:
            api.abort(503, "Unable to connect to sqlite3")
        cnx.close()

        return {
            "message": f"The stop_id {id} was removed from the database.",
            "stop_id": id
        }, 200

    @api.response(404, 'Stop not found')
    @api.response(400, 'Validation Error')
    @api.response(503, 'Bad Gateway Error')
    @api.response(200, 'Successful')
    @api.expect(putParser, validate=True)
    @api.expect(stop_model, validate=True)
    @api.param('name', description='The name of the stop',
               example="Leipzig")
    @api.param('last_updated', description='The datetime of most recent update',
               example="2020-06-23-12:58:39")
    @api.param('latitude', description='The latitude of the stop location',
               example=-13.8406)
    @api.param('longitude', description='The longitude of the stop location',
               example=-8.5720)
    @api.param('next_departure', description='The platform and direction of the next departure from this stop',
               example="Platform 3 towards Leipzig")
    @api.doc(description="Update a stop by its ID")
    def put(self, id):
        df = querySQLDatabase(db_file, f'SELECT * FROM "{table_name}" WHERE id = "{id}"')

        if id not in list(df['id']):
            api.abort(404, f"The stop_id {id} was not found in the database.", stop_id=id)

        cnx = sqlite3.connect(db_file)
        cur = cnx.cursor()

        args = putParser.parse_args(strict=True)

        stop_fields = {}
        for a in args.keys():
            field = args.get(a)
            if field is None:
                continue
            if a not in stop_model.keys():
                api.abort(400, f"Argument '{a}' not permitted")
            # check name and next_departure fields are not blank
            if a in ['name', 'next_departure'] and field == "":
                api.abort(400, f"Argument '{a}' cannot be blank: ''")
            # check last_updated in correct format
            if a in ['last_updated']:
                try:
                    tmp = datetime.strptime(field, "%Y-%m-%d-%H:%M:%S")
                except ValueError:
                    api.abort(400, f"Argument '{a}' not in format 'YYYY-MM-DD-HH:MM:SS'")
            stop_fields[a] = field

        if not stop_fields:
            api.abort(400, 'No request arguments given')

        # update values to SQLite
        for f in stop_fields.keys():
            try:
                updateValues(cnx, cur, table_name, f, id, stop_fields[f])
            except sqlite3.Error:
                api.abort(503, "Unable to connect to sqlite3")
            df.loc[id, f] = stop_fields[f]

        # update last_updated if not already done
        if 'last_updated' not in stop_fields.keys():
            tmp = datetime.now().replace(microsecond=0).strftime("%Y-%m-%d-%H:%M:%S")
            try:
                updateValues(cnx, cur, table_name, 'last_updated', id, tmp)
            except sqlite3.Error:
                api.abort(503, "Unable to connect to sqlite3")
            df.loc[id, 'last_updated'] = tmp

        cnx.close()
        return {
            'stop_id': id,
            'last_updated': df.loc[id, 'last_updated'],
            '_links': {
                'self':
                    {
                        'href': df.loc[df['id'] == id, '_links_self'].values[0]
                    }
            }
        }, 200


@api.route('/operator-profiles/<int:id>')
@api.param('id', description='The Stop identifier', example=1234567)
class OperatorProfiles(Resource):
    @api.response(404, 'Stop not found')
    @api.response(503, 'Bad Gateway Error')
    @api.response(200, 'Successful')
    @api.doc(description="Get all operator profiles by stop ID")
    def get(self, id):
        df = querySQLDatabase(db_file, f'SELECT * FROM "{table_name}" WHERE id = "{id}"')

        if id not in list(df['id']):
            api.abort(404, f"The stop_id {id} was not found in the database.", stop_id=id)

        operators = requestOperators(id)
        profiles = []

        # call gemini to generate a description for each operator
        for op in operators:
            question = f"Write a 1 paragraph description about {op}, "
            question += "who operates in the Deutsche Bahn train network in Germany"
            profiles.append({
                'name': op,
                'information': generate_content(question)
            })

        return {
            'stop_id': id,
            'profiles': profiles
        }, 200


@api.route('/guide')
class Guides(Resource):
    @api.response(400, 'Validation failed')
    @api.response(200, 'Successful')
    @api.produces(["text/txt"])
    @api.doc(description="Get a tourism guide as a .txt file")
    def get(self):
        df = getAll(db_file)
        if len(df.index) == 0:
            api.abort(400, f"Cannot create guide: the database is empty")
        if len(df.index) < 2:
            api.abort(400, f"Cannot create guide: database has not enough points of interest")

        from_id, to_id, journeys = findStopsWithRoute(df)
        if from_id is None:
            api.abort(400, f"Cannot create guide: no route exists between any two stops in the database")

        # Find journey that maximises stops in our database
        maxJourneyStops = []
        for j in journeys['journeys']:
            stopovers = []
            for s in j['legs'][0]['stopovers']:
                if s['stop']['id'] not in [from_id, to_id] and s['stop']['id'] in list(df['id']):
                    stopovers.append(s['stop']['id'])
            if len(stopovers) > len(maxJourneyStops):
                maxJourneyStops = stopovers

        from_name = df.loc[df['id'] == from_id, 'name'].values[0]
        to_name = df.loc[df['id'] == to_id, 'name'].values[0]

        # Call Gemini to get info about each point
        question = f"Create a tourism guide for travelling between {from_name} and {to_name} "
        if maxJourneyStops:
            stop_id = maxJourneyStops[0]
            stop_name = df.loc[df['id'] == stop_id, 'name'].values[0]
            question += f"via {stop_name} "
            for i in maxJourneyStops[1:]:
                stop_name = df.loc[df['id'] == i, 'name'].values[0]
                question += f"and {stop_name} "
        question += "in the Deutsche Bahn train network. "
        question += f"Include substantial information about {from_name} and {to_name}, "
        question += "and any key attractions or points of interest between these locations."
        content = generate_content(question)

        # save to file and return it
        filename = f"{studentid}.txt"
        with open(filename, 'w+') as f:
            f.write(content)

        file_path = os.path.join(curr_dir, filename)
        try:
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            api.abort(503, f"An error occurred sending the txt file: {e}")


# Request from deutsche bahn API
def requestStops(query):
    """
    Request to get stops that match query and return the result
    :param query: the query used to add stops
    :return: list of dicts containing stop objects
    """
    r = requests.get("https://v6.db.transport.rest/locations", params={
        'query': query,
        'poi': True,
        'results': 5
    })
    if r.status_code == 503:
        api.abort(503, "Unable to connect to Deutsche Bahn API")
    # add max. no. of stops returned
    resp = r.json()
    resp = [x for x in resp if x['type'] == 'stop']
    return resp


def requestNextDeparture(id):
    """
    Request to get departures for a stop id and return the top result

    Precondition: id is a valid id which exists in db
    :param id: the id of the stop
    :return: string containing next departure details, or None if not found
    """
    r = requests.get(f"https://v6.db.transport.rest/stops/{id}/departures", params={
        'duration': 120
    })
    if r.status_code == 503:
        api.abort(503, "Unable to connect to Deutsche Bahn API")
    resp = r.json()['departures']
    for r in resp:
        if r['direction'] is not None and r['platform'] is not None:
            dep_str = f"Platform {r['platform']} towards {r['direction']}"
            return dep_str
    return None


def requestOperators(id):
    """
    Request to get operator names for a stop id and return all results

    Precondition: id is a valid id which exists in db
    :param id: the id of the stop
    :return: list of operator names
    """
    operators = []

    r = requests.get(f"https://v6.db.transport.rest/stops/{id}/departures", params={
        'duration': 90,
        'results': 5
    })
    if r.status_code == 503:
        api.abort(503, "Unable to connect to Deutsche Bahn API")
    resp = r.json()['departures']
    for r in resp:
        if r['line'] is not None and r['line']['operator'] is not None and r['line']['operator']['name'] is not None:
            operators.append(r['line']['operator']['name'])

    # return only unique operator names
    return list(set(operators))


def requestJourneys(fromid, toid):
    """
    Request to get journey from fromid to toid and return the result

    Precondition: fromid and toid are valid ids which exist in db
    :param fromid: the id of the source stop
    :param toid: the id of the destination stop
    :return: list of dicts storing journeys between the stops
    """
    r = requests.get("https://v6.db.transport.rest/journeys", params={
        'from': fromid,
        'to': toid,
        'transfers': 2,
        'stopovers': True,
        'tickets': True,
        'scheduledDays': True,
        # 'results': 1
    })
    if r.status_code == 503:
        api.abort(503, "Unable to connect to Deutsche Bahn API")
    resp = r.json()
    return resp


# Gemini API
def generate_content(question):
    """
    Generate content by calling Gemini API and return the result as text

    :param question: the prompt to generate content from
    :return: the text output from the API
    """
    response = gemini.generate_content(question)
    try:
        result = response.text
    except Exception as e:
        api.abort(503, f"Unable to connect to Gemini API: {e}")
    else:
        return result


# SQLite management
def isSQLite3(filename):
    """
    Predicate checking if file exists
    In particular, used to check if database file exists or contains any data

    :param filename: name of the file
    :return: True if file exists, False otherwise
    """
    if not os.path.isfile(filename):
        return False
    if os.path.getsize(filename) < 100: # SQLite database file header is 100 bytes
        return False
    return True


def createSQLDatabase(df, data, filename, tablename):
    """
    Creates a new sqlite database, or update data values if exists

    :param df: dataframe storing data to insert/update
    :param data: dict storing data to insert/update
    :param filename: name of the file
    :param tablename: name of the table
    :return: response object
    """
    cnx = sqlite3.connect(filename)
    cur = cnx.cursor()

    if not isSQLite3(os.path.join(curr_dir, filename)):
        # create a new database
        df.to_sql(name=tablename, con=cnx, if_exists='replace')
        return {"message": "Data successfully created"}, 201

    # update existing values:
    for d in data:
        tmp_df = pd.read_sql_query(f"SELECT * FROM {tablename} WHERE {tablename}.id = '{d['id']}'", cnx)
        if not list(tmp_df.index):
            # add new values
            try:
                insertValues(cnx, cur, tablename, d)
            except sqlite3.Error:
                api.abort(503, "Unable to connect to sqlite3")
            continue

        # update existing values
        for c in list(tmp_df.columns):
            # ID must never be changed
            if c == 'id' or c == 'index':
                continue
            at = tmp_df.at[0, c]
            if d[c] != at:
                try:
                    updateValues(cnx, cur, tablename, c, d['id'], d[c])
                except sqlite3.Error:
                    api.abort(503, "Unable to connect to sqlite3")

    cnx.close()
    return {"message": "Data successfully updated"}, 200


def insertValues(cnx, cur, tablename, data):
    """
    Insert values into SQLite database

    :param cnx: database connection
    :param cur: database cursor
    :param tablename: name of the table
    :param data: data to insert
    """
    insert_sql = 'INSERT INTO {} ({}) VALUES ({})'.format(
        tablename,
        ','.join(data.keys()),
        ','.join(['?'] * len(data)))
    cur.execute(insert_sql, tuple(data.values()))
    cnx.commit()


def updateValues(cnx, cur, tablename, col, id, val):
    """
    Update values in SQLite database matching id and col with val

    :param cnx: database connection
    :param cur: database cursor
    :param tablename: name of the table
    :param col: column in table to update
    :param id: stop id belonging to row in table to update
    :param val: value to replace
    """
    update_sql = f'UPDATE "{tablename}" SET {col} = ? WHERE id = ?'
    cur.execute(update_sql, (val, id))
    cnx.commit()


def deleteValues(cnx, cur, tablename, id):
    """
    Delete a row matching id in SQLite database

    :param cnx: database connection
    :param cur: database cursor
    :param tablename: name of the table
    :param id: the id of the stop
    """
    delete_sql = f'DELETE FROM "{tablename}" WHERE id = ?'
    cur.execute(delete_sql, (id,))
    cnx.commit()


def querySQLDatabase(filename, query):
    """
    Extracts data from SQLite using given query

    :param filename: the name of the file
    :param query: the SQL query used to get data
    :return: dataframe storing retrieved data
    """
    cnx = sqlite3.connect(filename)
    df = pd.read_sql_query(query, cnx)
    cnx.close()
    return df


def getAll(filename):
    """
    Extracts all data from SQLite

    :param filename: the name of the file
    :return: dataframe storing retrieved data
    """
    return querySQLDatabase(filename, f'SELECT * from "{table_name}"')


def getIds(filename):
    """
    Extracts ids from SQLite and returns as a list

    :param filename: the name of the file
    :return: list of all ids in database
    """
    cnx = sqlite3.connect(filename)
    df = pd.read_sql_query(f'select id from "{table_name}"', con=cnx)
    cnx.close()
    return list(df['id'])


def getLink(filename, id):
    """
    Extracts the self link from SQLite matching id

    :param filename: the name of the file
    :param id: the id of the stop
    :return: the link of the stop id as a string
    """
    cnx = sqlite3.connect(filename)
    df = pd.read_sql_query(f'select _links_self from "{table_name}" where id = "{id}"', con=cnx)
    cnx.close()
    return df.at[0, '_links_self']


# Other helper functions
def getAdjLinks(filename, id):
    """
    Obtain links for self, next and prev of given id

    :param filename: the name of the file
    :param id: the id of the stop
    :return: dict storing self, next and prev links
    """
    ids_list = getIds(filename)
    links = {}
    # get next and prev links
    for i in range(len(ids_list)):
        if ids_list[i] == id:
            if i == 0 and i == len(ids_list) - 1:
                links = {
                    'self': {
                        'href': getLink(db_file, id),
                    }
                }
            elif 0 < i < len(ids_list) - 1:
                links = {
                    'self': {
                        'href': getLink(db_file, id),
                    },
                    'next': {
                        'href': getLink(db_file, ids_list[i + 1])
                    },
                    'prev': {
                        'href': getLink(db_file, ids_list[i - 1])
                    }
                }
            elif i == len(ids_list) - 1:
                links = {
                    'self': {
                        'href': getLink(db_file, id),
                    },
                    'prev': {
                        'href': getLink(db_file, ids_list[i - 1])
                    }
                }
            elif i == 0:
                links = {
                    'self': {
                        'href': getLink(db_file, id),
                    },
                    'next': {
                        'href': getLink(db_file, ids_list[i + 1])
                    }
                }
            break

    return links


def findStopsWithRoute(df):
    """
    Finds a pair of stop_ids from db where a route exists between them
    Returns the pair of stop_ids and the journey response object
    or None if none exists

    :param df: dataframe storing SQLite data
    :return:
    - from_id: the id of the source stop
    - to_id: the id of the destination stop
    - resp: journeys object
    or None for all the above return objects if no route exists between any pair of stop_ids
    """
    ids_lst = list(df['id'])
    for i in range(len(ids_lst)):
        for j in range(i + 1, len(ids_lst)):
            resp = requestJourneys(ids_lst[i], ids_lst[j])
            if resp is not None:
                try:
                    resp['journeys']
                except KeyError:
                    # journey does not exist or error occurred
                    continue
                if True not in resp['journeys'][0]['scheduledDays'].values():
                    # cancelled journey
                    continue
                return ids_lst[i], ids_lst[j], resp
    return None, None, None


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
