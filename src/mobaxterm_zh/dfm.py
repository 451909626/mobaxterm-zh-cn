"""Lossless Delphi binary form reader; offsets permit display-only resource patches."""
import struct

class Reader:
    def __init__(self, data):
        self.data = data
        self.p = 0
        self.values = []
        self.components = []

    def take(self, n):
        if n < 0 or self.p+n > len(self.data):
            raise ValueError(f'Out of bounds at {self.p} length {n}')
        b = self.data[self.p:self.p+n]
        self.p += n
        return b

    def byte(self):
        return self.take(1)[0]

    def short(self):
        return self.take(self.byte()).decode('cp1252')

    def value(self, component, prop):
        start = self.p
        t = self.byte()
        if t in (0, 8, 9, 13):
            value = {0:None, 8:False, 9:True, 13:None}[t]
        elif t == 1:
            value = []
            while self.data[self.p] != 0:
                value.append(self.value(component, prop+'[]'))
            self.p += 1
        elif t in (2, 3, 4, 19):
            value = int.from_bytes(self.take({2:1, 3:2, 4:4, 19:8}[t]),'little',signed=True)
        elif t in (5, 15, 16, 17, 21):
            value = self.take({5:10, 15:4, 16:8, 17:8, 21:8}[t]).hex()
        elif t in (6, 7):
            value = self.short()
        elif t in (12, 18, 20):
            length = int.from_bytes(self.take(4),'little')
            value = self.take(length*(2 if t==18 else 1)).decode({12:'cp1252',18:'utf-16le',20:'utf-8'}[t])
        elif t == 10:
            length = int.from_bytes(self.take(4),'little')
            self.take(length)
            value = {'binary_bytes': length}
        elif t == 11:
            value = []
            while self.data[self.p] != 0:
                value.append(self.short())
            self.p += 1
        elif t == 14:
            value = []
            while self.data[self.p] != 0:
                if self.data[self.p] in (2,3,4):
                    self.value(component, prop+'.index')
                assert self.byte()==1, (self.p,t)
                item = {}
                while self.data[self.p] != 0:
                    name = self.short()
                    item[name] = self.value(component, prop+'.'+name)
                self.p += 1
                value.append(item)
            self.p += 1
        else:
            raise ValueError(f'Unknown type {t} at {start} {component}.{prop}')
        self.values.append({'component':component,'property':prop,'type':t,'value':value,'start':start,'end':self.p})
        return value

    def component(self, parent=''):
        flags = 0
        if self.data[self.p] & 0xf0 == 0xf0:
            flags = self.byte() & 0xf
            if flags & 2:
                self.value(parent, '$child_position')
        cls = self.short()
        name = self.short()
        path = parent+'.'+name if parent else name
        self.components.append({'path':path,'class':cls,'name':name,'flags':flags})
        while self.data[self.p] != 0:
            prop = self.short()
            self.value(path, prop)
        self.p += 1
        while self.data[self.p] != 0:
            self.component(path)
        self.p += 1

    def read(self):
        assert self.take(4)==b'TPF0'
        self.component()
        assert self.p == len(self.data), (self.p,len(self.data))
        return self

def encode_text(text):
    # vaWString is converted by the Delphi reader using the active Windows code page.
    raw = text.encode('utf-16le')
    return bytes([18])+struct.pack('<I',len(raw)//2)+raw
