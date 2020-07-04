import re

__author__  = "Marlon Trifunovic"
__license__ = "MIT License"
__url__     = "https://github.com/MarlonTri/lab_data_process",


##Example barcodes for record types
#plate_carrier          - APER1391
#plate_carrier_extra    - P0000000
#tube_rack              - S0000000


BC_PATTERNS = [
    ("plate_carrier", "APER\d{4}"),
    ("plate_carrier_extra", "P\d{7}"),
    ("tube_rack","S\d+")
    ]


def read_file(file_path):
    with open(file_path,"r") as f:
        txt = f.read()
    txt_records = re.findall("BEGIN_RECORD.*?END_RECORD", txt, re.DOTALL)
    return txt_records


class records_file(object):
    """
    object representing an input file:
        records of:
            1 plate_carrier,
            1 plate_carrier_extra,
            necessary amount of tube_racks
    """
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
        
    def plates_wells(self, mapping_mode):
        """
        this generator will iterate along all the plate positions, taking into account missing plates and pool_number
        supported mapping_modes:
            'elution',
            'pcr_quadrant',
            'pcr_interleave'
        """
        if mapping_mode == "elution":
            #assign barcodes to elution plates
            for plate_bc in self.plate_carrier.barcodes:
                if plate_bc!="":
                    for pool_itr in range(self.pool_num):
                        for number in range(1,13):
                            for letter in "abcdefgh":
                                yield (plate_bc,pool_itr,letter+str(number))
        elif mapping_mode == "pcr_quadrant":
            print("quadrant")
            #assign barcodes to one big barcode plate, assigning in quadrants
            #starting in top left and rotating clockwise
            letters_lst = ["abcdefgh","ijklmnop"]
            x_plate_offsets = [0,12]
            for i in range(4):
                x_off = x_plate_offsets[i%2]
                letters = letters_lst[i//2]
                for pool_itr in range(self.pool_num):
                    for number in range(1+x_off,13+x_off):
                        for letter in letters:
                            yield (self.plate_carrier.barcodes[i],pool_itr,letter+str(number))
        elif mapping_mode == "pcr_interleave":
            letters = "abcdefghijklmnop"
            #assign barcodes to one pcr barcode plate, but interleaving 4 plates
            for i in range(4):
                x_off = i%2
                for pool_itr in range(self.pool_num):
                    for number in range(12):
                        for letter_num in range(8):
                            pos = letters[2*letter_num+i//2]+str(x_off+2*number+1)
                            yield (self.plate_carrier.barcodes[i],pool_itr,pos)
        else:
            raise Exception(f"Unknown type of plate mapping: {mapping_mode}")

    def tube_rack_samples(self):
        """
        this generator will spit out the tube_rack samples in order that they are encountered in the file
        it will output empty strings for the sample that have no barcodes
        """
        for tube_rack in self.tube_racks:
            for tube_rack_bc in tube_rack.barcodes:
                yield tube_rack_bc    
    
    def fill_wells_output(self, mapping_mode):
        """given a type of output, will generate output mapping as csv string """
        num_plate_slots = len(list(self.plates_wells(mapping_mode)))
        num_samples = len(list(self.tube_rack_samples()))
        if num_plate_slots!= num_samples:
            raise Exception(f"The amount of plate wells times the"
                            f"pool number({num_plate_slots}) does not"
                            f"equal the number of sample entries({num_samples})")

        output = "PLATE_BARCODE,POOL_ITR,PLATE_POS,SAMPLE_BARCODE\n"
        for plate_info,sample_bc in zip(self.plates_wells(mapping_mode),self.tube_rack_samples()):
            plate_bc,pool_itr,plate_pos = plate_info
            output += f"{plate_bc},{pool_itr},{plate_pos},{sample_bc}\n"
        return output
    def save_to_file(self,output_name):
        """save the output to file, for all three different types of output"""
        with open(output_name + "_elution.txt","w") as f:
            f.write(records.fill_wells_output("elution"))
        with open(output_name + "_pcr_quadrant.txt","w") as f:
            f.write(records.fill_wells_output("pcr_quadrant"))
        with open(output_name + "_pcr_interleave.txt","w") as f:
            f.write(records.fill_wells_output("pcr_interleave"))

    def __str__(self): 
        s = f"Pool Number:\t{self.pool_num}\n"
        s += f"Tube Rack Amt:\t{len(self.tube_racks)}\n"
        s += "Plate Record:\n\t" + str(self.plate_carrier).replace("\n","\n\t")
        s += "\nAlt Plate Record:\n\t" + str(self.plate_carrier_extra).replace("\n","\n\t") 
        return s
        

class record(object):
    """object representing a record from the file"""
    def __init__(self, txt):
        self.time_stamp = re.search("\d{4}-\d\d-\d\d \d\d:\d\d:\d\d",txt).group()

        lines = re.split("\n+",txt)
        raw_type = re.split("\W",lines[1])
        self.type_position = int(raw_type[1])
        self.barcode = raw_type[2]
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
        s = f"Type:\t\t{self.type}\n"
        s += f"Barcode: \t{self.barcode}\n"
        s += f"Time:\t\t{self.time_stamp}\n"
        s += f"Type Pos:\t{self.type_position}\n"
        s += "Data Entries:\n"
        s+=f"\tPos\tBarcode\n\n"
        for pos,barcode in enumerate(self.barcodes):
            s+=f"\t{pos}\t{barcode}\n"
        return s

if __name__=="__main__":
    #example on how to save to file
    records = records_file("test_data/input.txt",5) #pool number
    records.save_to_file("test_data/output") #no file extension needed


                                
