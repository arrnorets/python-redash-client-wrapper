#!/usr/bin/python3

# -*- coding: utf-8 -*-

from configparser import ConfigParser
from redashAPI import RedashAPIClient
import argparse
import datetime
import json
import os
import sys

def getOptions():
    ''' This function simply parses commandline options and returns them back
    to the script.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument( '--cfg', dest = 'cfgfile', action = 'store', required = True, help = 'Path to configuration file' )
    parser.add_argument( '--redash', dest = 'redash', action = 'store', required = True, help = 'Name of redash server attributes from cfgfile' )
    parser.add_argument( '--ds', dest = 'datasource', action = 'store', required = True, help = 'Datasource to select' )
    parser.add_argument( '--table', dest = 'table', action = 'store', required = True, help = 'Table tpo select from' )
    parser.add_argument( '--getdesc', dest = 'getdesc', action = 'store_true', required = False, help = 'Get table description and exit' )
    parser.add_argument( '--limit', dest = 'limit', action = 'store', required = False, help = 'Query result limit.', default=1000 )
    parser.add_argument( '--order', dest = 'order', action = 'store', required = False, help = 'Query sort order.', default='datetime DESC' )
    parser.add_argument( '--fields', dest = 'fields', action = 'store', required = False, help = 'Fields to select', default='*' )
    parser.add_argument( '--constraints', dest = 'constraints', action = 'store', required = False, help = 'Constraints for WHERE clause', default=None )
    parser.add_argument( '--constraint_delimiter', dest = 'constraint_delimiter', action = 'store', required = False, help = 'Constraints delimiter', default=';;' )
    parser.add_argument( '--from_ts', dest = 'from_ts', action = 'store', required = False, help = '"From" time value for selection interval', default=None )
    parser.add_argument( '--to_ts', dest = 'to_ts', action = 'store', required = False, help = '"To" time value for selection interval', default=None )
    parser.add_argument( '--lastmin', dest = 'lastmin', action = 'store', required = False, type = int, help = 'Print logs for last N minutes', default=None )
    return parser.parse_args()
    
def prepareRedashInstance(redashName: str, redashServerConfig: dict):
    '''Prepare redash instance. Exit if creation was unsuccessful, 
    e.g. because of wrong credentials.
    '''
    redashInstance = None
    
    if not redashName in redashServerConfig.keys():
        print(F"Cannot find definition of {redashName} server in config file.")
        sys.exit(3)
    redashServerAttributes = redashServerConfig[redashName].split(';')
    if len(redashServerAttributes) == 3:
        redashInstance = RedashAPIClient(redashServerAttributes[1], redashServerAttributes[0], redashServerAttributes[2] )
    elif len(redashServerAttributes) == 2:
        redashInstance = RedashAPIClient(redashServerAttributes[1], redashServerAttributes[0] )
    else:
        print("Wrong Redash attributes string. Must be <endpoint>:<token>:(<path to file with cookies>)?")
        sys.exit(4)
    return redashInstance

def getDatasourceName(datasource: str, dsConfig: dict):
    '''Optionally transform datasource name according to config settings'''
    if datasource not in dsConfig.keys():
        return datasource
    else:
        return dsConfig[datasource]
    
def getDatasourceID(redash: RedashAPIClient, dsName: str):
    '''Transforms datasource name into dsID. Exit if it was unsuccessful'''
    for ds in redash.get('data_sources').json():
         if ds['name'] == dsName:
             return ds['id']
    print( F"Cannot find appropriate datasource {dsName} on specified redash server.")
    sys.exit(5)

def getAvailableFields(redash: RedashAPIClient, dsID : int, args):
    '''Just print available fields from the table and exit'''
    availableFields = []
    try:
        result = redash.query_and_wait_result(dsID, F"describe table {args.table}", 5)
        for row in result.json()["query_result"]["data"]["rows"]:
            availableFields.append(row['name'])
    except Exception as e:
        print("Cannnot get description")
        sys.exit(7)
    print(availableFields)
    sys.exit(0)

def prepareSelectPart(args):
    return F"SELECT {args.fields} FROM {args.table} "

def prepareWhereClause(args):
    '''Prepare clauses for WHERE'''
    if args.constraints is not None:
        constraintsArray = args.constraints.split(args.constraint_delimiter)
        clause = F" {constraintsArray[0]}"
        for c in range(1, len(constraintsArray)):
            clause = F" {clause} AND {constraintsArray[c]}"
        return clause
    else:
        return None

def calculateTimeInterval(args):
    '''Calculate DateTime interval'''
    if args.lastmin is not None:
        from_ts = str(datetime.datetime.now() - datetime.timedelta(minutes=args.lastmin)).split('.')[0]
        to_ts = str(datetime.datetime.now()).split('.')[0]
        return F" datetime > toDateTime('{from_ts}') AND datetime < toDateTime('{to_ts}') "
    elif args.from_ts is not None and args.to_ts is not None:
        return F" datetime > toDateTime('{args.from_ts}') AND datetime < toDateTime('{args.to_ts}') "
    else:
        return None

def main():
    redash = None
    dsName = None
    dsID = None
    queryName = None
    redashQuery = None
    statement = None
    
    args = getOptions()
    
    if not os.path.exists(args.cfgfile):
        print(F"File {args.cfgfile} was not found.")
        sys.exit(1)
    
    c = ConfigParser()
    # parse existing file
    c.read(args.cfgfile)
    if not 'redash-servers' in c.sections():
        print("Cfgfile must contain the following sections: redash-servers")
        sys.exit(2) 
    redash = prepareRedashInstance( args.redash, c['redash-servers'] )
    if 'datasources' in c.sections():
        dsName = getDatasourceName( args.datasource, c['datasources'])
    else:
        dsName = args.datasource     
    dsID = getDatasourceID(redash, dsName)
    
    if args.getdesc is True:
        getAvailableFields(redash, dsID, args)
    else:
        selectPart = prepareSelectPart(args)
        timeInterval = calculateTimeInterval(args)
        clauses = prepareWhereClause(args)
        
        if timeInterval is not None and clauses is not None:
            statement = F"{selectPart} WHERE {timeInterval} AND {clauses} ORDER BY {args.order} LIMIT {args.limit}"
        elif timeInterval is not None:
            statement = F"{selectPart} WHERE {timeInterval} ORDER BY {args.order} LIMIT {args.limit}"
        elif clauses is not None:
            statement = F"{selectPart} WHERE {clauses} ORDER BY {args.order} LIMIT {args.limit}"
            
        print(F" The query is : {statement}")
        try:
            result = redash.query_and_wait_result(dsID, statement, 60)
            for row in result.json()["query_result"]["data"]["rows"]:
                print(row)
        except Exception as e:
            print(F"Cannot execute statement {statement}")
            
    sys.exit(0)
        
if __name__ == '__main__':
    main()



