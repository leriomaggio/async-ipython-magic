"""This is a sample script file, run and invoked directly 
by an iPython notebook (i.e. "iPython Run Test.ipynb").

This is just to see how the `%run` iPython magic works
with external executions.
"""

import os
import argparse
import sys

class DummyClass():
    """Dummy class just defined to see how namespace
    integration works"""
    
    def __init__(self, class_name):
        self._class_name = class_name
        
    @property
    def name(self):
        return self._class_name
    
    
dummy_global = DummyClass('Global Scope')
print('Created Instance: dummy_global')


def main():
    current_path = os.path.abspath(os.path.curdir)
    print('Current Path: ', current_path)
    
    print('Sys Argv: ', sys.argv)
    
    dummy_local = DummyClass('Local Scope')
    print('Instance: dummy_local')
    print('Name: ', dummy_local.name)
    

def main_heavy():
    N = 10**7
    s = sum([i**3 for i in range(N)])
    return s
    

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Simple or Heavy Execution.')
    parser.add_argument('--mode', dest='mode', type=str, choices=['simple', 'heavy'],
                        default='simple', help='the execution mode (i.e. Simple or Heavy)')
    
    args = parser.parse_args()
    
    if args.mode == 'simple':
        # Simple, Lightweight, execution
        main()
        
        dummy_main = DummyClass('Main Scope')
        print('Instance: dummy_main')
        print('Name (in Main): ', dummy_main.name)
    else:  # heavy
        s = main_heavy()
        print('sum: ', s)