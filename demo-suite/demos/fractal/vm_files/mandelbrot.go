// Copyright 2012 Google Inc. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"bytes"
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"log"
	"math"
	"math/cmplx"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
)

var (
	colors             [numColors]color.RGBA
	logEscape          float64
	minValue, maxValue float64
	debugLog           *log.Logger
	tileServers        []string
)

const (
	// The number of iterations of the Mandelbrot calculation.
	// More iterations mean higher quality at the cost of more CPU time.
	iterations = 4000

	// The size of an edge of the tile by default
	defaultTileSize = 256
	maxTileSize     = 1024

	// Size, in pixels, of the mandelbrot set at zoom 0
	baseZoomSize = 400

	// Making this value higher will make the colors cycle faster
	colorDensity = 50

	// The number of colors that we cycle through
	numColors = 5000

	// How many times we run the easing loop.  Higher numbers will be sharper
	// transitions between color stops.
	colorRampEase = 2

	// The final tile size that actually gets rendered
	leafTileSize = 128

	enableDebugLog = false
)

func initLogger() {
	if enableDebugLog {
		debugLog = log.New(os.Stderr, "DEBUG ", log.LstdFlags)

	} else {
		null, _ := os.Open(os.DevNull)
		debugLog = log.New(null, "", 0)
	}
}

func initMath() {
	minValue = math.MaxFloat64
	maxValue = 0
}

func isPowerOf2(num int) bool {
	return (num & (num - 1)) == 0
}

// The official Google Colors!
var colorStops = []color.Color{
	color.RGBA{0x00, 0x99, 0x25, 0xFF}, // Green
	color.RGBA{0x33, 0x69, 0xE8, 0xFF}, // Blue
	color.RGBA{0xD5, 0x0F, 0x25, 0xFF}, // Red
	color.RGBA{0xEE, 0xB2, 0x11, 0xFF}, // Yellow
	color.RGBA{0xFF, 0xFF, 0xFF, 0xFF}, // White
}

var centerColor = color.RGBA{0x66, 0x66, 0x66, 0xFF} // Gray

func interpolateColor(c1, c2 color.Color, where float64) color.Color {
	r1, g1, b1, a1 := c1.RGBA()
	r2, g2, b2, a2 := c2.RGBA()

	var c color.RGBA64
	c.R = uint16((float64(r2)-float64(r1))*where + float64(r1) + 0.5)
	c.G = uint16((float64(g2)-float64(g1))*where + float64(g1) + 0.5)
	c.B = uint16((float64(b2)-float64(b1))*where + float64(b1) + 0.5)
	c.A = uint16((float64(a2)-float64(a1))*where + float64(a1) + 0.5)
	return c
}

func initColors() {
	cIndex := 0
	numColorsLeft := numColors
	numStopsLeft := len(colorStops)
	prevStop := colorStops[len(colorStops)-1]
	for _, stop := range colorStops {
		debugLog.Println(stop)
		numColorsInStop := numColorsLeft / numStopsLeft
		debugLog.Println(numColorsInStop, numColorsLeft, numStopsLeft)

		for i := 0; i < numColorsInStop; i++ {
			where := float64(i) / float64(numColorsInStop)

			// This is a sigmoidal-ish easing function as described here:
			// http://sol.gfxile.net/interpolation/
			for j := 0; j < colorRampEase; j++ {
				where = where * where * (3 - 2*where)
			}
			//where = math.Pow(where, colorRampEase)
			c := interpolateColor(prevStop, stop, where)
			colors[cIndex] = color.RGBAModel.Convert(c).(color.RGBA)
			cIndex++
		}

		prevStop = stop
		numColorsLeft -= numColorsInStop
		numStopsLeft--
	}

	// for _, c := range colors {
	// 	debugLog.Printf("%v", c)
	// }
}

func tileHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")

	x, _ := strconv.Atoi(r.FormValue("x"))
	y, _ := strconv.Atoi(r.FormValue("y"))
	z, _ := strconv.Atoi(r.FormValue("z"))
	tileSize, err := strconv.Atoi(r.FormValue("tile-size"))
	if err != nil {
		tileSize = defaultTileSize
	}
	if tileSize <= 0 || tileSize > maxTileSize || !isPowerOf2(tileSize) {
		w.WriteHeader(http.StatusBadRequest)
		return
	}

	var b []byte
	if tileSize > leafTileSize && len(tileServers) > 0 {
		b = downloadAndCompositeTiles(x, y, z, tileSize)
	} else {
		b = renderImage(x, y, z, tileSize)
	}
	w.Header().Set("Content-Type", "image/png")
	w.Header().Set("Content-Length", strconv.Itoa(len(b)))
	w.Write(b)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	fmt.Fprintln(w, "ok")
}

func quitHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	fmt.Fprintln(w, "ok")

	log.Println("Exiting process on /debug/quit")

	// Wait 500ms and then exit the process
	go func() {
		time.Sleep(500 * time.Millisecond)
		os.Exit(1)
	}()
}

func downloadAndCompositeTiles(x, y, z, tileSize int) []byte {
	resultImg := image.NewRGBA(image.Rect(0, 0, tileSize, tileSize))

	subTileCount := tileSize / leafTileSize
	subTileXStart := x * subTileCount
	subTileYStart := y * subTileCount

	c := make(chan TileResult)
	for subX := subTileXStart; subX < subTileXStart+subTileCount; subX++ {
		for subY := subTileYStart; subY < subTileYStart+subTileCount; subY++ {
			debugLog.Printf("Spawing goroutine to render x: %v y: %v z: %v",
				subX, subY, z)
			go func(subX, subY int) {
				c <- downloadAndDecodeImage(subX, subY, z, leafTileSize)
			}(subX, subY)
		}
	}

	// Loop to get each image.  As they come in composite it into the destination
	// image.  An alternative would be to composite into the target image in the
	// goroutine but that might not be threadsafe.
	for i := 0; i < subTileCount*subTileCount; i++ {
		result := <-c
		if result.img != nil {
			debugLog.Printf("Compositing result for x: %v y: %v", result.x, result.y)
			localTileOrigin := image.Pt((result.x-subTileXStart)*leafTileSize,
				(result.y-subTileYStart)*leafTileSize)
			destRect := result.img.Bounds().Add(localTileOrigin)
			draw.Draw(resultImg, destRect, result.img, image.ZP, draw.Src)
		} else {
			debugLog.Printf("No image returned for x: %v y: %v", result.x, result.y)
		}
	}

	buf := new(bytes.Buffer)
	png.Encode(buf, resultImg)
	return buf.Bytes()
}

type TileResult struct {
	x   int
	y   int
	img *image.RGBA
}

func downloadAndDecodeImage(x, y, z, tileSize int) TileResult {
	tileResult := TileResult{x: x, y: y}

	v := url.Values{}
	v.Set("x", strconv.Itoa(x))
	v.Set("y", strconv.Itoa(y))
	v.Set("z", strconv.Itoa(z))
	v.Set("tile-size", strconv.Itoa(tileSize))
	u := url.URL{
		Scheme:   "http",
		Host:     tileServers[rand.Intn(len(tileServers))],
		Path:     "/tile",
		RawQuery: v.Encode(),
	}

	// Get the image
	debugLog.Println("GETing:", u.String())
	httpResult, err := http.Get(u.String())
	if err != nil {
		log.Printf("Error GETing %v: %v", u.String(), err)
		return tileResult
	}
	debugLog.Println("GET success:", u.String())

	// Decode that puppy
	img, _, _ := image.Decode(httpResult.Body)
	tileResult.img = img.(*image.RGBA)
	httpResult.Body.Close()

	return tileResult
}

// mandelbrotColor computes a Mandelbrot value and then assigns a color from the
// color table.
func mandelbrotColor(c complex128, zoom int) color.RGBA {
	// Scale so we can fit the entire set in one tile when zoomed out.
	c = c*3.5 - complex(2.5, 1.75)

	z := complex(0, 0)
	iter := 0
	for ; iter < iterations; iter++ {
		z = z*z + c
		r, i := real(z), imag(z)
		absSquared := r*r + i*i
		if absSquared >= 4 {
			// This is the "Continuous (smooth) coloring" described in Wikipedia:
			// http://en.wikipedia.org/wiki/Mandelbrot_set#Continuous_.28smooth.29_coloring
			v := float64(iter) - math.Log2(math.Log(cmplx.Abs(z))/math.Log(4))

			// We are scaling the value based on the zoom level so things don't get
			// too busy as we get further in.
			v = math.Abs(v) * float64(colorDensity) / math.Max(float64(zoom), 1)
			minValue = math.Min(float64(v), minValue)
			maxValue = math.Max(float64(v), maxValue)
			colorIdx := (int(v) + numColors*zoom/len(colorStops)) % numColors
			return colors[colorIdx]
		}
	}

	return centerColor
}

func renderImage(x, y, z, tileSize int) []byte {
	// tileX and tileY is the absolute position of this tile at the current zoom
	// level.
	numTiles := int(1 << uint(z))
	tileX, tileY := x*tileSize, y*tileSize
	scale := 1 / float64(numTiles*baseZoomSize)

	debugLog.Printf("Rendering Tile x: %v y: %v z: %v tileSize: %v tileX: %v tileY: %v scale: %v", x, y, z, tileSize, tileX, tileY, scale)

	img := image.NewRGBA(image.Rect(0, 0, tileSize, tileSize))
	for i := 0; i < tileSize; i++ {
		for j := 0; j < tileSize; j++ {
			c := complex(float64(tileX+i)*scale, float64(tileY+j)*scale)
			img.SetRGBA(i, j, mandelbrotColor(c, z))
		}
	}

	debugLog.Printf("Render Done. Value range min: %f, max: %f", minValue, maxValue)

	// Add a sleep to simulate a more complex computation.  This scales with the
	// number of pixels rendered.
	//time.Sleep(time.Duration(tileSize*tileSize/50) * time.Microsecond)

	buf := new(bytes.Buffer)
	png.Encode(buf, img)
	return buf.Bytes()
}

func main() {
	runtime.GOMAXPROCS(runtime.NumCPU())
	initLogger()
	initColors()
	initMath()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/tile", tileHandler)
	http.HandleFunc("/debug/quitquitquit", quitHandler)

	// Support opening multiple ports so that we aren't bound by HTTP connection
	// limits in browsers.
	portBase := flag.Int("portBase", 8900, "The base port.")
	numPorts := flag.Int("numPorts", 10, "Number of ports to open.")
	tileServersArg := flag.String("tileServers", "",
		"Downstream tile servers to use when doing composited rendering.")
	flag.Parse()

	// Go is super regular with string splits.  An empty string results in a list
	// with an empty string in it.  It is logical but a pain.
	tileServers = strings.Split(*tileServersArg, ",")
	di, si := 0, 0
	for ; si < len(tileServers); si++ {
		tileServers[di] = strings.TrimSpace(tileServers[si])
		if len(tileServers[di]) > 0 {
			di++
		}
	}
	tileServers = tileServers[:di]
	log.Printf("Tile Servers: %q", tileServers)

	for i := 0; i < *numPorts; i++ {
		portSpec := fmt.Sprintf("0.0.0.0:%v", *portBase+i)
		go func() {
			log.Println("Listening on", portSpec)
			err := http.ListenAndServe(portSpec, nil)
			if err != nil {
				log.Fatal("ListenAndServe: ", err)
			}
		}()
	}

	select {}
}
