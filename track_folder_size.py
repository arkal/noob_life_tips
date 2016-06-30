from __future__ import print_function
from collections import defaultdict, Counter
import argparse
import json
import os
import time


def trackDirSizes(workDir, outfile):
    '''
    '''
    dirs = defaultdict(dict)
    strikes = 0
    leadingSlashes = workDir.count('/')
    iters = 1
    while True:
        dirsViewed = set()
        print('Running Iteration %s...' % iters, end=' ')
        for dirPath, dirNames, fileNames in os.walk(workDir):
            if len(dirPath.split('/')) == leadingSlashes + 4:
                # leading /a/b/c + /toil-<wfid>/tmpxyx/UUID
                #       = 3 + 1 + 1 + 1 + 1 for the leading '' (since split on '/' == ['', ''])
                dirSize, dirFiles = getDirStats(dirPath)
                if dirPath not in dirs:
                    dirs[dirPath]['size'] = dirSize
                    dirs[dirPath]['files'] = dirFiles
                else:
                    if dirSize > dirs[dirPath]['size']:
                        dirs[dirPath]['size'] = dirSize
                    for fileName, fileSize in dirFiles.items():
                        if fileSize > dirs[dirPath]['files'][fileName]:
                            dirs[dirPath]['files'][fileName] = fileSize
            dirsViewed.add(dirPath)
        completedJobs = set(dirs.keys()) - dirsViewed
        for job in completedJobs:
            with open(outfile, 'a') as outFH:
                json.dump({job: dirs[job]}, outFH)
                print('', sep='', end='\n', file=outFH)
            dirs.pop(job)
        if len(dirsViewed) == 0:
            strikes += 1
            if strikes == 3:
                print('Done.\n\n RUN COMPLETED')
                break
        else:
            strikes = 0
        print('Done. Sleeping for 10s')
        if strikes != 0:
            print('Strike %s' % strikes) 
        time.sleep(10)
        iters += 1
    return None

def getDirStats(workDir):
    '''
    '''
    allFiles = Counter()
    totalSize = 0
    for dirPath, dirNames, fileNames in os.walk(workDir):
        folderSize, filesInFolder = _getDirSize(dirPath, fileNames)
        totalSize += folderSize
        allFiles.update(filesInFolder)
    return totalSize, allFiles


def _getDirSize(dirPath, fileNames):
    '''
    Returns the size of the directory including all linked files provided their inode was not in
    linkedFileInodes.

    :param str dirPath: Dir path
    :param list fileNames: Files in the directory
    :param set linkedFileInodes: set of inode numbers of files that have multiple links, and
                                 have already been acccounted for.
    :return: Size of the directory
    '''
    folderSize = 0
    filesInFolder = {}
    for f in fileNames:
        fp = os.path.join(dirPath, f)
        try:
            fileStats = os.stat(fp)
        except OSError as err:
            if err.errno == 2:
                # This means the file got deleted while we were reading it
                continue
            else:
                raise
        folderSize += fileStats.st_size
        filesInFolder[fp] = fileStats.st_size
    return folderSize, filesInFolder

def parseOutput(infile, outfile):
    """
    Parse the output from trackDirSizes
    """
    with open(infile) as inFH, open(outfile, 'w') as outFH:
        for line in inFH:
            linedict = json.loads(line)
            foldername = linedict.keys()[0]
            print('#', foldername, file=outFH)
            print('# Total Size =', linedict[foldername]['size'], file=outFH)
            for key, value in linedict[foldername]['files'].items():
                print(key, value, sep="\t", file=outFH)
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workDir')
    parser.add_argument('-o', '--outfile_prefix', dest='outfile_prefix', required=False,
                        default='~/trackedFileSizes')
    params = parser.parse_args()
    params.outfile_prefix = os.path.expanduser(params.outfile_prefix)
    params.workDir = os.path.abspath(params.workDir).rstrip('/')
    open(params.outfile_prefix + '_raw.txt', 'w').close()
    trackDirSizes(params.workDir, params.outfile_prefix + '_raw.txt')
    parseOutput(params.outfile_prefix + '_raw.txt', params.outfile_prefix + '_filtered.tsv')