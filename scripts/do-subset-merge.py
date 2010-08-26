#! /usr/bin/env python
import sys
import khmer
import gc
import Queue
import threading
import glob
import os.path
import shutil

dir1 = sys.argv[1]
dir2 = sys.argv[2]

K=32
N_THREADS = 1

ht = khmer.new_hashtable(K, 1)

###

lock = threading.Lock()
output_n = 0

###

def pull_pair(q):
    while q.qsize() >= 2:
        try:
            ht, filename1 = q.get(False)
        except Queue.Empty:
            print 'exiting'
            return

        try:
            ht, filename2 = q.get(False)
        except Queue.Empty:
            print 'pushing, then exiting'
            q.put(ht, filename1)
            return
        
        merge_file = merge(filename1, filename2, ht)
        #q.put((ht, merge_file))   # @CTB

def load(filename):
    pmap_filename = filename
    surr_filename = filename[:-4] + 'surr'
    subset = ht.load_subset_partitionmap(pmap_filename, surr_filename)
    return subset

def merge(filename1, filename2, ht):
    global output_n, lock

    lock.acquire()
    next_n = output_n
    output_n += 1
    lock.release()

    merge_filename = os.path.join(dir2, '%s.merge.%d' % (dir2, next_n))
    print 'merge: %s = %s + %s' % (merge_filename, filename1, filename2)
    subset1 = load(filename1)
    subset2 = load(filename2)
    ht.merge2_subset(subset1, subset2)

    ht.save_subset_partitionmap(subset1, merge_filename + '.pmap',
                                merge_filename + '.surr')
    return merge_filename + '.pmap'

# detect all of the relevant partitionmap files
subset_filenames = glob.glob(os.path.join(dir1, '*.pmap'))

# put on queue
merge_queue = Queue.Queue()
for filename in subset_filenames:
    merge_queue.put((ht, filename))

print 'starting threads'

threads = []
for n in range(N_THREADS):
    t = threading.Thread(target=pull_pair, args=(merge_queue,))
    threads.append(t)
    t.start()

# wait for threads
for t in threads:
    t.join()

# done!

if merge_queue.qsize() == 1:
    ht, merge_file = merge_queue.get()
    shutil.copy(merge_file, os.path.join(dir2, os.path.basename(merge_file)))
    surr_file = merge_file[:-4] + 'surr'
    shutil.copy(surr_file, os.path.join(dir2, os.path.basename(surr_file)))
    
assert merge_queue.qsize() == 0
#ht, merge_file = merge_queue.get()
#print 'final subset in:', merge_file
