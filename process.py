import re

##Barcode formats for records

#plate_carrier          - APER1391
#plate_carrier_extra    - P0000000
#tube_rack              - S0000000
#plate                  - ??????

BC_PATTERNS = [ ("plate_carrier", "APER\d{4}"),
                ("plate_carrier_extra", "P\d{7}"),
                ("tube_rack","S\d+")
                           ]


def read_file(file_path):
    with open(file_path,"r") as f:
        txt = f.read()
    txt_records = re.findall("BEGIN_RECORD.*?END_RECORD", txt, re.DOTALL)
    return txt_records

class records_file(object):
    def __init__(self, file_path, pool_num):
        self.pool_num = pool_num
        txt_records = read_file(file_path)
        self.records = [record(txt) for txt in txt_records]
        def select_and_assert(name):
            selected = [record for record in self.records if record.type==name]
            if len(selected)!=1:
                raise Exception(f"No records of the type \"{name}\" in the file")
            return selected[0]
        self.plate_carrier = select_and_assert("plate_carrier")
        self.plate_carrier_extra = select_and_assert("plate_carrier_extra")
        self.tube_racks = [record for record in self.records if record.type=="tube_rack"]
        
        plate_bc_list = [x[1] for x in self.plate_carrier.barcodes]
        rack_bc_list = sum([[x[1] for x in tube_rack.barcodes] for tube_rack in self.tube_racks],[])

        for bc in plate_bc_list:
            if plate_bc_list.count(bc)>1 and bc!="":
                raise Exception(f"plate barcode {bc} appears multiple times in file")
        for bc in rack_bc_list:
            if rack_bc_list.count(bc)>1 and bc!="":
                raise Exception(f"sample barcode {bc} appears multiple times in file")
        num_plates = len([plate for _,plate in self.plate_carrier.barcodes if plate!=""])
        if len(self.tube_racks)!=pool_num*num_plates:
            pass#raise Exception(f"There are {len(self.tube_racks)} tube_rack records but there should be {pool_num*num_plates}")
        
    def plates_wells(self):
        for plate_pos,plate_bc in self.plate_carrier.barcodes:
            if plate_bc!="":
                for pool_itr in range(self.pool_num):
                    for number in range(1,13):
                        for letter in "abcdefgh":
                            yield (plate_bc,pool_itr,letter+str(number))

    def tube_rack_samples(self):
        for tube_rack in self.tube_racks:
            for tube_rack_pos,tube_rack_bc in tube_rack.barcodes:
                yield tube_rack_bc    
    
    def fill_wells(self):
        #assert len(list(self.plates_wells()))==len(list(self.tube_rack_samples()))
        output = "PLATE_BARCODE,POOL_ITR,PLATE_POS,SAMPLE_BARCODE\n"
        for plate_info,sample_bc in zip(self.plates_wells(),self.tube_rack_samples()):
            output += ",".join([str(x) for x in plate_info+(sample_bc,)])
            output += "\n"
        return output

class record(object):
    def __init__(self, txt):
        self.time_stamp = re.search("\d{4}-\d\d-\d\d \d\d:\d\d:\d\d",txt).group()

        lines = re.split("\n+",txt)
        raw_type = re.split("\W",lines[1])
        self.type_position = int(raw_type[1])
        info = [re.split("\W",x) for x in lines[2:-1]]
        self.barcodes = [(int(pos),barcode) for _,pos,barcode in info]

        self.type = ""
        for record_type,record_pattern in BC_PATTERNS:
            if re.match(record_pattern, raw_type[2]):
                if self.type!="" and self.type!=record_type:
                    raise Exception(f"Multiple record patterns matched: {self.type} and {record_type}")
                self.type = record_type
        if self.type=="":
            raise Exception(f"No record matches on raw string:\n\t\"{raw_type}\"\n")
            
    def __str__(self):
        s = f"Type:\t{self.type}\n"
        s += f"Time:\t{self.time_stamp}\n"
        s += f"Type Pos:\t{self.type_position}\n"
        s += "Data Entries:\n"
        for pos,barcode in self.barcodes:
            s+=f"\t{pos}\t{barcode}\n"
        return s
        
records = records_file("input.txt",5)
print(records.fill_wells())



                                
