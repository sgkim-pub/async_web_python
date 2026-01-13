import os

def loadQuery(fileName):
    filePath = os.path.join('app', 'common', 'queries', fileName)
    with open(filePath, 'r') as fp:
        query = fp.read()

    return query
