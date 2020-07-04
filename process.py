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
    """object representing an input file:records of plate_carrier, plate_carrier_extra, and necessary amount of tube_racks"""
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
        
        rack_bc_list = sum([tube_rack.barcodes for tube_rack in self.tube_racks],[])

        for bc in self.plate_carrier.barcodes:
            if self.plate_carrier.barcodes.count(bc)>1 and bc!="":
                raise Exception(f"plate barcode {bc} appears multiple times in file")
        for bc in rack_bc_list:
            if rack_bc_list.count(bc)>1 and bc!="":
                raise Exception(f"sample barcode {bc} appears multiple times in file")
        num_plates = len([plate for plate in self.plate_carrier.barcodes if plate!=""])
        if len(self.tube_racks)!=3*pool_num*num_plates:
            raise Exception(f"There are {len(self.tube_racks)} tube_rack records but there should be {pool_num*num_plates}")
        
    def plates_wells(self, mode):
        """
        this will iterate along all the plate positions, taking into account missing plates and pool_number
        supported modes: 'elusion','pcr','pcr_interleave'
        """
        if mode == "elusion":
            #assign barcodes to elusion plates
            for plate_bc in self.plate_carrier.barcodes:
                if plate_bc!="":
                    for pool_itr in range(self.pool_num):
                        for number in range(1,13):
                            for letter in "abcdefgh":
                                yield (plate_bc,pool_itr,letter+str(number))
        elif mode == "pcr":
            #assign barcodes to one big barcode plate, assigning in quadrants
            letters_lst = ["abcdefgh","ijklmnop"]
            x_plate_offsets = [0,12]
            for i in range(4):
                x_off = i%2
                for letters in letters_lst[i//2]:
                    for pool_itr in range(self.pool_num):
                        for number in range(1+x_off,13+x_off):
                            for letter in letters:
                                yield (self.plate_carrier.barcodes[i],pool_itr,letter+str(number))
        elif mode == "pcr_interleave":
            letters = "abcdefghijklmnop"
            #assign barcodes to one big barcode plate, but interleaving 4 plates
            for i in range(4):
                x_off = i%2
                for pool_itr in range(self.pool_num):
                    for number in range(12):
                        for letter_num in range(8):
                            pos = letters[2*letter_num+i//2]+str(x_off+2*number+1)
                            yield (self.plate_carrier.barcodes[i],pool_itr,pos)
        else:
            raise Exception("Unknown type of plate mapping")

    def tube_rack_samples(self):
        for tube_rack in self.tube_racks:
            for tube_rack_bc in tube_rack.barcodes:
                yield tube_rack_bc    
    
    def fill_wells_output(self, pcr_plate):
        num_plate_slots = len(list(self.plates_wells(pcr_plate)))
        num_samples = len(list(self.tube_rack_samples()))
        if num_plate_slots!= num_samples:
            raise Exception(f"The amount of plate wells times the"
                            f"pool number({num_plate_slots}) does not"
                            f"equal the number of sample entries({num_samples})")

        output = "PLATE_BARCODE,POOL_ITR,PLATE_POS,SAMPLE_BARCODE\n"
        for plate_info,sample_bc in zip(self.plates_wells(pcr_plate),self.tube_rack_samples()):
            plate_bc,pool_itr,plate_pos = plate_info
            output += f"{plate_bc},{pool_itr},{plate_pos},{sample_bc}\n"
        return output
    def save_to_file(self,output_name):
        with open(output_name + "_elusion.txt","w") as f:
            f.write(records.fill_wells_output("elusion"))
        with open(output_name + "_pcr.txt","w") as f:
            f.write(records.fill_wells_output("pcr"))
        with open(output_name + "_pcr_interleave.txt","w") as f:
            f.write(records.fill_wells_output("pcr_interleave"))
        

class record(object):
    """object representing a record from the file"""
    def __init__(self, txt):
        self.time_stamp = re.search("\d{4}-\d\d-\d\d \d\d:\d\d:\d\d",txt).group()

        lines = re.split("\n+",txt)
        raw_type = re.split("\W",lines[1])
        self.type_position = int(raw_type[1])

        self.type = ""
        for record_type,record_pattern in BC_PATTERNS:
            if re.match(record_pattern, raw_type[2]):
                if self.type!="" and self.type!=record_type:
                    raise Exception(f"Multiple record patterns matched: {self.type} and {record_type}")
                self.type = record_type
        if self.type=="":
            raise Exception(f"No record matches on raw string:\n\t\"{raw_type}\"\n")

        if "plate_carrier" in self.type:
            info = [re.split("\W",x) for x in lines[3:-1]]
        else:
            info = [re.split("\W",x) for x in lines[2:-1]]
        self.barcodes = [barcode for _,_,barcode in info]


            
    def __str__(self):
        s = f"Type:\t{self.type}\n"
        s += f"Time:\t{self.time_stamp}\n"
        s += f"Type Pos:\t{self.type_position}\n"
        s += "Data Entries:\n"
        for pos,barcode in enumerate(self.barcodes):
            s+=f"\t{pos}\t{barcode}\n"
        return s
        
records = records_file("input.txt",5)
records.save_to_file("output")


                                
