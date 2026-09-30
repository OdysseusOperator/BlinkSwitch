package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime"
	"sort"
	"strings"
	"time"
	"unsafe"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	apiURL   = "http://127.0.0.1:5555/screenassign"
	fontPath = "frontend/fonts/MonaspaceNeonFrozen-Medium.ttf"
	ipcPath  = "/tmp/blinkswitch-frontend.sock"
	width    = int32(720)
	height   = int32(430)
)

var currentFont rl.Font

type item struct {
	Type           string `json:"type"`
	ID             string `json:"id"`
	Title          string `json:"title"`
	ExeName        string `json:"exe_name"`
	AppName        string `json:"app_name"`
	AppDisplayName string `json:"app_display_name"`
	HWND           int64  `json:"hwnd"`
	ChromeWindowID *int64 `json:"chrome_window_id"`
}

type switcherData struct {
	Windows []item         `json:"windows"`
	Tabs    []item         `json:"tabs"`
	MRU     map[string]int `json:"mru"`
}

type frontend struct {
	client      *http.Client
	items       []item
	filtered    []item
	mru         map[string]int
	query       string
	selected    int
	lastFetch   time.Time
	loading     bool
	status      string
	statusUntil time.Time
	visible     bool
	toggle      chan struct{}
}

func clayError(errorData clay.ErrorData) {
	fmt.Printf("Clay error: %s\n", errorData.ErrorText)
}

func measureText(text clay.StringSlice, config *clay.TextElementConfig, _ unsafe.Pointer) clay.Dimensions {
	size := rl.MeasureTextEx(currentFont, text.String(), float32(config.FontSize), 1)
	return clay.Dimensions{Width: size.X, Height: size.Y}
}

func rayColor(color clay.Color) rl.Color {
	return rl.Color{R: uint8(color.R), G: uint8(color.G), B: uint8(color.B), A: uint8(color.A)}
}

func renderClay(commands clay.RenderCommandArray) {
	for i := int32(0); i < commands.Length; i++ {
		command := clay.RenderCommandArray_Get(&commands, i)
		box := command.BoundingBox
		switch command.CommandType {
		case clay.RENDER_COMMAND_TYPE_RECTANGLE:
			rl.DrawRectangle(int32(box.X), int32(box.Y), int32(box.Width), int32(box.Height), rayColor(command.RenderData.Rectangle.BackgroundColor))
		case clay.RENDER_COMMAND_TYPE_TEXT:
			text := command.RenderData.Text
			rl.DrawTextEx(currentFont, text.StringContents.String(), rl.Vector2{X: box.X, Y: box.Y}, float32(text.FontSize), 1, rayColor(text.TextColor))
		}
	}
}

func text(value string, size uint16, color clay.Color) {
	clay.Text(value, clay.TextConfig(clay.TextElementConfig{FontSize: size, TextColor: color}))
}

func appKey(value item) string {
	for _, candidate := range []string{value.ExeName, value.AppName, value.AppDisplayName} {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	return "unknown"
}

func label(value item) string {
	app := value.AppDisplayName
	if app == "" {
		app = value.AppName
	}
	if app == "" {
		app = value.ExeName
	}
	if app == "" {
		app = "Unknown app"
	}
	title := strings.TrimSpace(value.Title)
	if title == "" {
		title = "(untitled)"
	}
	if value.Type == "tab" {
		return fmt.Sprintf("%s - %s [tab]", app, title)
	}
	return fmt.Sprintf("%s - %s", app, title)
}

func (f *frontend) fetch() {
	f.loading = true
	defer func() { f.loading = false }()
	response, err := f.client.Get(apiURL + "/windows-and-tabs")
	if err != nil {
		f.status = "Backend unavailable"
		f.statusUntil = time.Now().Add(3 * time.Second)
		return
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		f.status = fmt.Sprintf("Backend returned %d", response.StatusCode)
		f.statusUntil = time.Now().Add(3 * time.Second)
		return
	}
	var data switcherData
	if err := json.NewDecoder(response.Body).Decode(&data); err != nil {
		f.status = "Invalid backend response"
		f.statusUntil = time.Now().Add(3 * time.Second)
		return
	}
	f.items = append(data.Windows, data.Tabs...)
	f.mru = data.MRU
	f.lastFetch = time.Now()
	f.filter()
}

func (f *frontend) filter() {
	query := strings.ToLower(strings.TrimSpace(f.query))
	f.filtered = f.filtered[:0]
	for _, value := range f.items {
		if query == "" || strings.Contains(strings.ToLower(label(value)), query) {
			f.filtered = append(f.filtered, value)
		}
	}
	sort.SliceStable(f.filtered, func(i, j int) bool {
		left := f.mru[appKey(f.filtered[i])]
		right := f.mru[appKey(f.filtered[j])]
		if left != right {
			return left > right
		}
		return strings.ToLower(label(f.filtered[i])) < strings.ToLower(label(f.filtered[j]))
	})
	if f.selected >= len(f.filtered) {
		f.selected = max(0, len(f.filtered)-1)
	}
}

func (f *frontend) touch(value item) {
	body := strings.NewReader(fmt.Sprintf(`{"app_key":%q}`, appKey(value)))
	response, err := f.client.Post(apiURL+"/mru/touch", "application/json", body)
	if err == nil {
		response.Body.Close()
	}
}

func (f *frontend) activate(value item) {
	f.touch(value)
	if value.Type == "tab" {
		// Browser focus remains a separate request because the extension owns tab activation.
		f.focusBrowserWindow(value)
		body := strings.NewReader(fmt.Sprintf(`{"tab_id":%q}`, value.ID))
		response, err := f.client.Post(apiURL+"/activate-tab", "application/json", body)
		if err == nil {
			response.Body.Close()
		}
		f.hide()
		return
	}
	body := strings.NewReader(fmt.Sprintf(`{"hwnd":%d}`, value.HWND))
	response, err := f.client.Post(apiURL+"/focus-window-only", "application/json", body)
	if err == nil {
		response.Body.Close()
	}
	f.hide()
}

func (f *frontend) show() {
	rl.ClearWindowState(rl.FlagWindowHidden)
	f.visible = true
}

func (f *frontend) hide() {
	rl.SetWindowState(rl.FlagWindowHidden)
	f.visible = false
}

func (f *frontend) toggleVisibility() {
	if f.visible {
		f.hide()
		return
	}
	f.show()
	f.query = ""
	f.selected = 0
	f.filter()
}

func (f *frontend) focusBrowserWindow(value item) {
	if value.ExeName == "" || value.ChromeWindowID == nil {
		return
	}

	browserWindows := make([]item, 0)
	for _, candidate := range f.items {
		if candidate.Type != "tab" && candidate.ExeName == value.ExeName && candidate.HWND > 0 {
			browserWindows = append(browserWindows, candidate)
		}
	}
	sort.Slice(browserWindows, func(i, j int) bool {
		return browserWindows[i].HWND < browserWindows[j].HWND
	})
	if len(browserWindows) == 0 {
		return
	}

	windowIDs := make([]int64, 0)
	seen := map[int64]bool{}
	for _, candidate := range f.items {
		if candidate.Type == "tab" && candidate.ExeName == value.ExeName && candidate.ChromeWindowID != nil {
			id := *candidate.ChromeWindowID
			if !seen[id] {
				seen[id] = true
				windowIDs = append(windowIDs, id)
			}
		}
	}
	sort.Slice(windowIDs, func(i, j int) bool { return windowIDs[i] < windowIDs[j] })
	index := 0
	for candidateIndex, id := range windowIDs {
		if id == *value.ChromeWindowID {
			index = candidateIndex
			break
		}
	}
	if index >= len(browserWindows) {
		index = len(browserWindows) - 1
	}
	body := strings.NewReader(fmt.Sprintf(`{"hwnd":%d}`, browserWindows[index].HWND))
	response, err := f.client.Post(apiURL+"/focus-window-only", "application/json", body)
	if err == nil {
		response.Body.Close()
	}
}

func (f *frontend) draw() {
	background := clay.Color{R: 50, G: 50, B: 50, A: 255}
	primary := clay.Color{R: 255, G: 255, B: 255, A: 255}
	muted := clay.Color{R: 135, G: 135, B: 135, A: 255}
	selection := clay.Color{R: 135, G: 206, B: 235, A: 255}
	clay.UI()(clay.ElementDeclaration{Id: clay.ID("Root"), Layout: clay.LayoutConfig{LayoutDirection: clay.TOP_TO_BOTTOM, Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)}, Padding: clay.PaddingAll(20), ChildGap: 10}, BackgroundColor: background}, func() {
		clay.UI()(clay.ElementDeclaration{Id: clay.ID("Header"), Layout: clay.LayoutConfig{Sizing: clay.Sizing{Width: clay.SizingGrow(0)}}}, func() {
			text("query: "+f.query, 24, primary)
		})
		clay.UI()(clay.ElementDeclaration{Id: clay.ID("List"), Layout: clay.LayoutConfig{LayoutDirection: clay.TOP_TO_BOTTOM, Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)}, ChildGap: 4}}, func() {
			if f.loading {
				text("loading...", 20, muted)
			}
			for index, value := range f.filtered {
				if index >= 12 {
					break
				}
				color := primary
				prefix := "  "
				if index == f.selected {
					color = selection
					prefix = "> "
				}
				text(prefix+label(value), 22, color)
			}
		})
		help := "Enter to switch | Esc to quit"
		if time.Now().Before(f.statusUntil) {
			help = f.status
		}
		text(help, 16, muted)
	})
}

func max(left, right int) int {
	if left > right {
		return left
	}
	return right
}

func startIPCListener(toggle chan<- struct{}) {
	if runtime.GOOS == "windows" {
		return
	}
	_ = os.Remove(ipcPath)
	listener, err := net.Listen("unix", ipcPath)
	if err != nil {
		fmt.Printf("IPC listener unavailable: %v\n", err)
		return
	}
	if err := os.Chmod(ipcPath, 0o600); err != nil {
		fmt.Printf("IPC socket permissions unavailable: %v\n", err)
	}
	go func() {
		defer listener.Close()
		for {
			connection, err := listener.Accept()
			if err != nil {
				return
			}
			_, _ = connection.Read(make([]byte, 1))
			_ = connection.Close()
			select {
			case toggle <- struct{}{}:
			default:
			}
		}
	}()
}

func notifyToggle() bool {
	if runtime.GOOS == "windows" {
		return false
	}
	connection, err := net.DialTimeout("unix", ipcPath, 500*time.Millisecond)
	if err != nil {
		return false
	}
	defer connection.Close()
	_, err = connection.Write([]byte("t"))
	return err == nil
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--toggle" {
		if notifyToggle() {
			return
		}
		os.Exit(1)
	}
	rl.SetConfigFlags(rl.FlagWindowUndecorated | rl.FlagWindowTopmost)
	rl.InitWindow(width, height, "BlinkSwitch Clay Frontend")
	defer rl.CloseWindow()
	rl.SetTargetFPS(60)

	currentFont = rl.LoadFontEx(fontPath, 64, nil, 0)
	if currentFont.Texture.ID == 0 {
		currentFont = rl.GetFontDefault()
	} else {
		defer rl.UnloadFont(currentFont)
	}

	arena := clay.CreateArenaWithCapacityAndMemory(make([]byte, clay.MinMemorySize()))
	clay.Initialize(arena, clay.Dimensions{Width: float32(width), Height: float32(height)}, clay.ErrorHandler{ErrorHandlerFunction: clayError})
	clay.SetMeasureTextFunction(measureText, unsafe.Pointer(&currentFont))

	f := &frontend{
		client:  &http.Client{Timeout: 500 * time.Millisecond},
		mru:     map[string]int{},
		visible: false,
		toggle:  make(chan struct{}, 1),
	}
	f.fetch()
	startHotkeyListener(f.toggle)
	startIPCListener(f.toggle)
	f.hide()
	for !rl.WindowShouldClose() {
		select {
		case <-f.toggle:
			f.toggleVisibility()
		default:
		}
		if time.Since(f.lastFetch) > 2*time.Second {
			f.fetch()
		}
		if !f.visible {
			time.Sleep(10 * time.Millisecond)
			continue
		}
		if rl.IsKeyPressed(rl.KeyEscape) {
			f.hide()
			continue
		}
		if rl.IsKeyPressed(rl.KeyDown) && f.selected < len(f.filtered)-1 {
			f.selected++
		}
		if rl.IsKeyPressed(rl.KeyUp) && f.selected > 0 {
			f.selected--
		}
		if rl.IsKeyPressed(rl.KeyEnter) && len(f.filtered) > 0 {
			f.activate(f.filtered[f.selected])
		}
		for character := rl.GetCharPressed(); character > 0; character = rl.GetCharPressed() {
			if character >= 32 && character <= 126 {
				f.query += string(rune(character))
				f.selected = 0
				f.filter()
			}
		}
		if rl.IsKeyPressed(rl.KeyBackspace) && len(f.query) > 0 {
			f.query = f.query[:len(f.query)-1]
			f.selected = 0
			f.filter()
		}

		clay.BeginLayout()
		f.draw()
		commands := clay.EndLayout()
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 50, G: 50, B: 50, A: 255})
		renderClay(commands)
		rl.EndDrawing()
	}
}
