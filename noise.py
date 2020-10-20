import math
import random
import xxhash
import time
from functools import lru_cache


chars = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "[::-1]

def smoothstep(x):
    if x <= 0:
        return 0
    elif x >= 1:
        return 1
    else:
        return x*x*(3 - 2*x)

def lerp(v0, v1, t):
    return v0 + t*(v1 - v0)

def smoothlerp(v0,v1,t):
    return lerp(v0,v1,smoothstep(t))

def hash_pos(seed,x,y):
    # we concat x and y for now
    # this probably won't be a problem i think?
    r=bytes()
    for v in (x,y):
        # normalise to be positive and things
        if v >= 0:
            v *= 2
            v += 1
        else:
            v = ((-v) * 2)
        v += 1
        # turn int into bytes but we need to know how many bytes for some reason
        # using only positive integers (as above) so that we don't have multiple positions that produce
        # the same byte values here
        l = math.floor(math.log2(v)/8)+1
        r += v.to_bytes(l,"big")
    # returns value between 0 and 1<<64
    return xxhash.xxh64_intdigest(r,seed=seed)

class Vec2D:
    # general vector class. could probably be optimised a bit by replacing with a dot(x0,y0,x1,y1) function etc, but oh well
    def __init__(self,x=0,y=0):
        self.x = x
        self.y = y
    def length(self):
        return math.sqrt(self.x**2 + self.y**2)
    def norm(self):
        l = self.length()
        if l == 0:
            return Vec2D(0,0)
        else:
            return self / l
    
    def __add__(self,other):
        return Vec2D(self.x+other.x, self.y+other.y)
    def __sub__(self,other):
        return Vec2D(self.x-other.x, self.y-other.y)
    def __mul__(self,scalar):
        return Vec2D(self.x*scalar,other.x*scalar)
    def __truediv__(self,scalar):
        return Vec2D(self.x/scalar, self.y/scalar)

    def __matmul__(self,other):
        # dot product 
        return (self.x*other.x) + (self.y*other.y)
    
    @classmethod
    def from_polar(cls,r,θ):
        return cls(r*math.cos(θ),r*math.sin(θ))

    def __repr__(self):
        return f"Vec2D({self.x},{self.y})"
    def __str__(self):
        return f"({self.x},{self.y})"


class PerlinNoise:
    def __init__(self,seed):
        self.vertices = dict()
        self.seed = seed
        self.cache = dict()

    def __repr__(self):
        return f"PerlinNoise({self.seed})"
    
    def vertex(self,x,y):
        x,y = int(x),int(y)
        if (x,y) in self.vertices:
            return self.vertices[x,y]
        else:
            θ = (2*math.pi / (1<<64)) * hash_pos(self.seed,x,y)
            vec = Vec2D.from_polar(1,θ)
            self.vertices[x,y] = vec 
            return vec

    def at(self,x,y):
        # i don't think it's actually possible to write a readable perlin noise implementation
        def dgg(ix,iy,x,y):
            vrt = self.vertex(ix,iy)
            off = Vec2D(x-ix,y-iy)
            return vrt @ off

        x0 = math.floor(x)
        x1 = x0 + 1
        y0 = math.floor(y)
        y1 = y0 + 1

        d00 = dgg(x0,y0,x,y)
        d01 = dgg(x0,y1,x,y)
        d10 = dgg(x1,y0,x,y)
        d11 = dgg(x1,y1,x,y)

        wx = x - x0
        wy = y - y0
        
        sy0 = smoothlerp(d00,d01,wy)
        sy1 = smoothlerp(d10,d11,wy)

        s = smoothlerp(sy0,sy1,wx)
        return s

class NoiseAggregator:
    # for multiple octaves, and things
    def __init__(self,octaves=[]):
        self.octaves = octaves
    def add(self,amplitude,scaling,generator):
        self.octaves.append((amplitude,scaling,generator))
    def at(self,x,y):
        # basically computes the weighted average of all the registered octaves, according to their amplitudes
        # so this will always return between -1 and 1 (assuming all the generators it's using do that as well)
        n = 0
        t = 0
        for amplitude,scaling,generator in self.octaves:
            n += amplitude
            t += amplitude * generator.at(scaling*x,scaling*y)
        return t/n

if __name__ == "__main__":
    # a fancy little noise generation demonstration
    # you can provide a seed on the command line if you want
    import sys
    if len(sys.argv) > 1:
        seed = xxhash.xxh64_intdigest(sys.argv[1])
    else:
        seed = random.randint(0,(1<<64)-1)
    octaves = []
    num_octaves = 3
    for i in range(num_octaves):
        amp = 2**i
        scl = 2**(num_octaves-i-1)
        gen = PerlinNoise(seed+i)
        octaves.append((amp,scl,gen))
    print(octaves)
    noise = NoiseAggregator(octaves)

    # note: we cache the results of the noise generators here, rather than in the noise generator classes themselves
    # because in the real use case we will store generated tiles in a database of some kind, and we will not be generating
    # noise for the same position as part of regular usage
    # you can think of this cache as being like that database in the real use case.
    @lru_cache(maxsize=10000)
    def noise_at(x,y):
        return noise.at(x,y)

    scale = 25 # change this to zoom the viewport in or out
    offset = 0
    while True:
        out = ""
        for pxy in range(40):
            for pxx in range(80):
                x = (pxx+offset) / (2*scale)
                y = (pxy+(offset/2)) / scale
                v = noise_at(x,y)
                c = chars[math.floor(((v+1)/2)*len(chars))]
                out += c
            out += "\n"
        print(chr(27)+"[2J"+out,end="")
        offset += 1
        time.sleep(0.05)




