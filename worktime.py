#!/usr/bin/env python3

#%%
from codecs import getdecoder
from os import times
from time import time
import arrow
import yaml

from enum import Enum
from dataclasses import dataclass

import click
import pathlib
import pyTextColor as ptc

# don't print yaml tags
yaml.emitter.Emitter.process_tag = lambda self, *args, **kw: None

#%% data structures
class RecordType(Enum):
    START = "start"
    END = "end"

@dataclass
class WorkRecord:
    type: RecordType
    timestamp: arrow.arrow.Arrow
    
    def __repr__(self) -> str:
        return f"WorkRecord({self.type.name}, {self.timestamp.format(fmt=arrow.FORMAT_RFC3339)})"

#%% serialization config

def workrecord_representer(dumper: yaml.SafeDumper, rec: WorkRecord) -> yaml.nodes.MappingNode:
  """Represent an WorkRecord instance as a YAML mapping node."""
  return dumper.represent_mapping("!WorkRecord", {
    "type": rec.type.name,
    "timestamp": rec.timestamp.format(fmt=arrow.FORMAT_RFC3339),
  })
  
def get_dumper():
  """Add representers to a YAML seriailizer."""
  safe_dumper = yaml.SafeDumper
  safe_dumper.add_representer(WorkRecord, workrecord_representer)
  return safe_dumper
  
#%%

def read_records(path: pathlib.Path) -> list[WorkRecord]:
    with open(path) as stream:
        record_dicts = yaml.load(stream, Loader=yaml.BaseLoader)
    if not record_dicts:
        return []
    records = list(
        map(lambda dt:  
            WorkRecord(
                RecordType[dt["type"]],
                arrow.get(dt["timestamp"],arrow.FORMAT_RFC3339)
                ),
            record_dicts))
    return records

def write_records(path: pathlib.Path,records: list[WorkRecord]) -> None:
    with open(path,"w") as stream:
        stream.write(yaml.dump(records,sort_keys=False, default_flow_style=False, Dumper=get_dumper()))
    
def make_record(type: RecordType) -> WorkRecord:
    timestamp = arrow.now()
    record = WorkRecord(type,timestamp)
    return record

def insert_record(path: pathlib.Path, rec: WorkRecord) -> None:
    records = read_records(path)
    if records and records[-1].type == rec.type:
        raise ValueError("Found Unexpected RecordType make sure that you have started/closed the last session!")
    records.append(rec)
    write_records(path,records)

# %%

WORKTIME_PATH = None
TC = ptc.pyTextColor()

@click.group()
@click.option('--path', envvar='WORKTIME_PATH',default=pathlib.Path.home() / ".worktime.yaml",type=click.Path(exists=False,dir_okay=False,writable=True,path_type=pathlib.Path))
def cli(path: pathlib.Path):
    path = path.resolve()
    
    if not path.exists():
        path.touch()
        print(f"created file {path}")
    
    global WORKTIME_PATH
    WORKTIME_PATH = path

@cli.command()
def start():
    record = make_record(RecordType.START)
    insert_record(WORKTIME_PATH,record)
    print(TC.format_text("WorkTime started",color="#fff0ff",bgcolor="green"))
    

@cli.command()
def stop():
    record = make_record(RecordType.END)
    insert_record(WORKTIME_PATH,record)
    print(TC.format_text("WorkTime stopped",color="#999999",bgcolor="blue"))
    
@cli.command()
def status():
    recs = read_records(WORKTIME_PATH)
    
    print(f"WorkTime\n{WORKTIME_PATH}\n")
    
    if not recs:
        print("no record yet")
        return
    
    last_rec = recs[-1]
    print(f"Current Status\n{last_rec.type.name} - {last_rec.timestamp.humanize()}")
    

if __name__ == "__main__":
    cli()