# lab_data_process
process.py takes as input the data format looking like multiple entries of "BEGIN_RECORD ... END_RECORD". 
The `records_file` object in process.py takes this input data format and parses it. Once parsed, `records_file` can output to file all 3 types of mappings in CSV format. If you'd like, you can also run `fill_wells_output` with a mapping mode to get the CSV output of a specific mapping mode.

Both the `records_file` and `record` object can be printed to the console as a string to see their internal data.
