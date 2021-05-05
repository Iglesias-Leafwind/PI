import os

def getFolders():
    results = []
    for root, dirs, files in os.walk('/home/anth0nypereira'):
        # print("root: " + root)
        # print("dirs: " + str(dirs))
        array = []
        root_parts = root.split("/")


        for path in dirs:
            if path[0] != "." and len(path) > 1:
                # print("good path: " + path) 
                if any(elem[0]=="." for elem in root_parts if len(elem) > 1):
                    # print("bad root: " + root)
                    continue
                else:
                    # print("good path: " + path + " and good root: " + root)
                    array = array + [path]
            else:
                continue
                # print (path + " has a . at the beginning")
        
        # print("\n \n \n \n")
        # print("--RESULTS--")
        for dir in array:
            # print("dirname: " + root)
            results = results + [os.path.join(root, dir)]
            # print(os.path.join(root, dir))
    return results

def main():
    result_list = getFolders()                
    for elem in result_list:
        print(elem)

main()