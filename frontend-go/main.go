package main

import (
	"encoding/json"
	"fmt"
	"io"
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
	DisplayAppName string `json:"display_app_name"`
	HWND           int64  `json:"hwnd"`
	ChromeWindowID *int64 `json:"chrome_window_id"`
}

type switcherData struct {
	Windows []item         `json:"windows"`
	Tabs    []item         `json:"tabs"`
	MRU     map[string]int `json:"mru"`
}

type command struct {
	name        string
	description string
}

type viewKind int

const (
	viewSwitcher viewKind = iota
	viewLayouts
	viewAssign
	viewWindows
	viewDetails
	viewSettings
)

var commands = []command{
	{name: "layouts", description: "Manage layouts"},
	{name: "assign", description: "Assign physical monitors to layout slots"},
	{name: "windows", description: "Manage windows"},
	{name: "settings", description: "Application settings"},
}

type frontend struct {
	client           *http.Client
	items            []item
	filtered         []item
	mru              map[string]int
	query            string
	selected         int
	lastFetch        time.Time
	loading          bool
	status           string
	statusUntil      time.Time
	visible          bool
	keepOpen         bool
	toggle           chan struct{}
	view             viewKind
	viewTitle        string
	viewHelp         string
	viewRows         []string
	layouts          []map[string]any
	settings         map[string]any
	activeLayout     string
	assignLayoutName string
	assignSlots      []map[string]any
	monitors         []map[string]any
	assignment       map[string]string
	textInput        bool
	textValue        string
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

func displayApp(value item) string {
	for _, candidate := range []string{value.DisplayAppName, value.AppDisplayName, value.AppName, value.ExeName} {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	return "Unknown app"
}

func label(value item) string {
	app := displayApp(value)
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

func (f *frontend) request(method string, path string, payload any, result any) error {
	var body io.Reader
	if payload != nil {
		encoded, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		body = strings.NewReader(string(encoded))
	}
	request, err := http.NewRequest(method, apiURL+path, body)
	if err != nil {
		return err
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	response, err := f.client.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		message, _ := io.ReadAll(response.Body)
		return fmt.Errorf("backend returned %d: %s", response.StatusCode, strings.TrimSpace(string(message)))
	}
	if result == nil {
		return nil
	}
	return json.NewDecoder(response.Body).Decode(result)
}

func (f *frontend) openView(view viewKind) {
	f.view = view
	f.selected = 0
	f.query = ""
	f.viewRows = nil
	f.viewHelp = "Esc to close"
	switch view {
	case viewLayouts:
		f.loadLayouts()
	case viewSettings:
		f.loadSettings()
	case viewAssign:
		f.loadAssignment()
	case viewWindows:
		f.loadWindowsView()
	}
}

func (f *frontend) loadLayouts() {
	var layouts []map[string]any
	if err := f.request(http.MethodGet, "/layouts", nil, &layouts); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.layouts = layouts
	f.viewTitle = "Layout Management"
	f.viewRows = make([]string, 0, len(layouts))
	for _, layout := range layouts {
		name := stringValue(layout["name"], "Unknown")
		fileName := stringValue(layout["file_name"], "")
		screens := intValue(layout["total_screens"])
		active := ""
		if strings.TrimSuffix(fileName, ".json") == f.activeLayout {
			active = " [ACTIVE]"
		}
		f.viewRows = append(f.viewRows, fmt.Sprintf("%s (%d screens)%s - %s", name, screens, active, stringValue(layout["description"], "")))
	}
	f.viewHelp = "Enter/A activate | D delete | N new | Esc close"
}

func (f *frontend) loadSettings() {
	var settings map[string]any
	if err := f.request(http.MethodGet, "/settings", nil, &settings); err != nil {
		f.showStatus(err.Error())
		return
	}
	var layouts []map[string]any
	if err := f.request(http.MethodGet, "/layouts", nil, &layouts); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.settings = settings
	f.layouts = layouts
	f.viewTitle = "Settings"
	f.viewRows = []string{
		fmt.Sprintf("Default Layout: %s", stringValue(settings["default_layout"], "(None)")),
		fmt.Sprintf("Center Mouse on Switch: %s", boolLabel(settings["center_mouse_on_switch"])),
	}
	f.viewHelp = "Up/Down navigate | Left/Right cycle layout | Enter toggle | Esc close"
}

func (f *frontend) loadWindowsView() {
	var windows []item
	if err := f.request(http.MethodGet, "/windows", nil, &windows); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.viewTitle = "Windows Management"
	f.viewRows = make([]string, 0, len(windows))
	for _, window := range windows {
		title := window.Title
		if len(title) > 50 {
			title = title[:47] + "..."
		}
		f.viewRows = append(f.viewRows, fmt.Sprintf("%s (%s)", title, window.ExeName))
	}
	f.viewHelp = "Enter configure | D delete rule | Esc close"
}

func (f *frontend) loadAssignment() {
	if len(f.layouts) == 0 {
		if err := f.request(http.MethodGet, "/layouts", nil, &f.layouts); err != nil {
			f.showStatus(err.Error())
			return
		}
	}
	layoutName := f.activeLayout
	if layoutName == "" && len(f.layouts) > 0 {
		layoutName = strings.TrimSuffix(stringValue(f.layouts[0]["file_name"], ""), ".json")
	}
	if layoutName == "" {
		f.viewTitle = "Assign Monitors to Slots"
		f.viewRows = []string{"No layouts found. Create a layout first."}
		return
	}
	var layout map[string]any
	if err := f.request(http.MethodGet, "/layouts/"+layoutName, nil, &layout); err != nil {
		f.showStatus(err.Error())
		return
	}
	var screenConfig struct {
		Monitors []map[string]any `json:"monitors"`
	}
	if err := f.request(http.MethodGet, "/screen-config", nil, &screenConfig); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.assignLayoutName = layoutName
	f.monitors = screenConfig.Monitors
	f.assignment = loadAssignments()[layoutName]
	if f.assignment == nil {
		f.assignment = map[string]string{}
	}
	data, _ := layout["data"].(map[string]any)
	requirements, _ := data["screen_requirements"].(map[string]any)
	f.assignSlots, _ = requirements["screens"].([]map[string]any)
	// JSON decoding uses []any for nested arrays, so normalize screen rows.
	if raw, ok := requirements["screens"].([]any); ok {
		f.assignSlots = make([]map[string]any, 0, len(raw))
		for _, value := range raw {
			if screen, ok := value.(map[string]any); ok {
				f.assignSlots = append(f.assignSlots, screen)
			}
		}
	}
	f.viewTitle = "Assign Monitors to Slots"
	f.viewHelp = "1-9 assign monitor | Up/Down navigate | S save | Esc cancel"
	f.rebuildAssignmentRows()
}

func (f *frontend) rebuildAssignmentRows() {
	f.viewRows = make([]string, 0, len(f.assignSlots)+len(f.monitors)+1)
	for index, slot := range f.assignSlots {
		slotNumber := intValue(slot["slot"])
		if slotNumber == 0 {
			slotNumber = index + 1
		}
		orientation := stringValue(slot["orientation"], "?")
		identity := f.assignment[fmt.Sprint(slotNumber)]
		if identity == "" {
			identity = "(unassigned)"
		}
		marker := "[ ]"
		if index == f.selected {
			marker = "[*]"
		}
		f.viewRows = append(f.viewRows, fmt.Sprintf("%s Slot %d (%s) -> %s", marker, slotNumber, orientation, identity))
	}
	f.viewRows = append(f.viewRows, "")
	for index, monitor := range f.monitors {
		f.viewRows = append(f.viewRows, fmt.Sprintf("%d: %s (%s, %dx%d)", index+1, stringValue(monitor["identity_key"], "?"), stringValue(monitor["orientation"], "?"), intValue(monitor["width"]), intValue(monitor["height"])))
	}
}

func (f *frontend) handleAssignmentInput() {
	if rl.IsKeyPressed(rl.KeyS) {
		assignments := loadAssignments()
		assignments[f.assignLayoutName] = f.assignment
		if err := saveAssignments(assignments); err != nil {
			f.showStatus(err.Error())
		} else {
			f.showStatus("Assignments saved")
		}
		return
	}
	if rl.IsKeyPressed(rl.KeyDown) && f.selected < len(f.assignSlots)-1 {
		f.selected++
		f.rebuildAssignmentRows()
	}
	if rl.IsKeyPressed(rl.KeyUp) && f.selected > 0 {
		f.selected--
		f.rebuildAssignmentRows()
	}
}

func loadAssignments() map[string]map[string]string {
	assignments := map[string]map[string]string{}
	data, err := os.ReadFile("frontend/assignment.json")
	if err != nil {
		return assignments
	}
	if err := json.Unmarshal(data, &assignments); err != nil {
		return map[string]map[string]string{}
	}
	return assignments
}

func saveAssignments(assignments map[string]map[string]string) error {
	data, err := json.MarshalIndent(assignments, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile("frontend/assignment.json", data, 0o600)
}

func (f *frontend) showStatus(message string) {
	f.status = message
	f.statusUntil = time.Now().Add(4 * time.Second)
}

func stringValue(value any, fallback string) string {
	if result, ok := value.(string); ok && result != "" {
		return result
	}
	return fallback
}

func intValue(value any) int {
	if result, ok := value.(float64); ok {
		return int(result)
	}
	if result, ok := value.(int); ok {
		return result
	}
	return 0
}

func boolLabel(value any) string {
	if result, ok := value.(bool); ok && result {
		return "ON"
	}
	return "OFF"
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
	if f.keepOpen {
		return
	}
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

func (f *frontend) executeCommand() {
	name := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(f.query)), "/")
	for _, entry := range commands {
		if entry.name == name {
			f.openView(map[string]viewKind{
				"layouts":  viewLayouts,
				"assign":   viewAssign,
				"windows":  viewWindows,
				"settings": viewSettings,
			}[entry.name])
			return
		}
	}
	f.showStatus("Unknown command: /" + name)
}

func (f *frontend) filteredCommands() []command {
	query := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(f.query)), "/")
	result := make([]command, 0, len(commands))
	for _, entry := range commands {
		if query == "" || strings.Contains(entry.name+" "+entry.description, query) {
			result = append(result, entry)
		}
	}
	return result
}

func (f *frontend) handleViewInput() {
	if f.textInput {
		if rl.IsKeyPressed(rl.KeyEscape) {
			f.textInput = false
			f.textValue = ""
		} else if rl.IsKeyPressed(rl.KeyEnter) {
			f.submitTextInput()
		} else if rl.IsKeyPressed(rl.KeyBackspace) && len(f.textValue) > 0 {
			f.textValue = f.textValue[:len(f.textValue)-1]
		}
		return
	}
	if f.view == viewSwitcher {
		if rl.IsKeyPressed(rl.KeyEscape) {
			f.hide()
			return
		}
		if strings.HasPrefix(strings.TrimSpace(f.query), "/") {
			matches := f.filteredCommands()
			if rl.IsKeyPressed(rl.KeyDown) && f.selected < len(matches)-1 {
				f.selected++
			}
			if rl.IsKeyPressed(rl.KeyUp) && f.selected > 0 {
				f.selected--
			}
		} else {
			if rl.IsKeyPressed(rl.KeyDown) && f.selected < len(f.filtered)-1 {
				f.selected++
			}
			if rl.IsKeyPressed(rl.KeyUp) && f.selected > 0 {
				f.selected--
			}
		}
		if rl.IsKeyPressed(rl.KeyEnter) {
			if strings.HasPrefix(strings.TrimSpace(f.query), "/") {
				matches := f.filteredCommands()
				if len(matches) > 0 && f.selected < len(matches) {
					f.query = "/" + matches[f.selected].name
				}
				f.executeCommand()
			} else if len(f.filtered) > 0 {
				f.activate(f.filtered[f.selected])
			}
		}
		return
	}

	if rl.IsKeyPressed(rl.KeyEscape) || rl.IsKeyPressed(rl.KeyBackspace) {
		f.view = viewSwitcher
		f.query = ""
		f.selected = 0
		f.filter()
		return
	}
	if rl.IsKeyPressed(rl.KeyDown) && f.selected < len(f.viewRows)-1 {
		f.selected++
	}
	if rl.IsKeyPressed(rl.KeyUp) && f.selected > 0 {
		f.selected--
	}

	switch f.view {
	case viewLayouts:
		f.handleLayoutsInput()
	case viewAssign:
		f.handleAssignmentInput()
	case viewSettings:
		f.handleSettingsInput()
	}
}

func (f *frontend) handleLayoutsInput() {
	if len(f.layouts) == 0 {
		if rl.IsKeyPressed(rl.KeyN) {
			f.textInput = true
			f.textValue = ""
		}
		return
	}
	if rl.IsKeyPressed(rl.KeyN) {
		f.textInput = true
		f.textValue = ""
		return
	}
	if rl.IsKeyPressed(rl.KeyEnter) || rl.IsKeyPressed(rl.KeyA) {
		layoutName := strings.TrimSuffix(stringValue(f.layouts[f.selected]["file_name"], ""), ".json")
		if layoutName == f.activeLayout {
			f.activeLayout = ""
			f.showStatus("Layout deactivated")
		} else {
			var result map[string]any
			assignment := loadAssignments()[layoutName]
			if assignment == nil {
				assignment = map[string]string{}
			}
			err := f.request(http.MethodPost, "/apply-rules", map[string]any{"layout_name": layoutName, "assignment": assignment}, &result)
			if err != nil {
				f.showStatus(err.Error())
			} else {
				f.activeLayout = layoutName
				f.showStatus("Layout activated: " + layoutName)
			}
		}
		f.loadLayouts()
	}
	if rl.IsKeyPressed(rl.KeyD) {
		layoutName := strings.TrimSuffix(stringValue(f.layouts[f.selected]["file_name"], ""), ".json")
		if err := f.request(http.MethodDelete, "/layouts/"+layoutName, nil, nil); err != nil {
			f.showStatus(err.Error())
		} else {
			f.showStatus("Layout deleted: " + layoutName)
			f.loadLayouts()
		}
	}
}

func (f *frontend) submitTextInput() {
	name := strings.TrimSpace(f.textValue)
	if name == "" {
		f.showStatus("Layout name cannot be empty")
		return
	}
	if err := f.request(http.MethodPost, "/layouts", map[string]any{"name": name, "description": ""}, nil); err != nil {
		f.showStatus(err.Error())
	} else {
		f.showStatus("Layout created: " + name)
		f.textInput = false
		f.textValue = ""
		f.loadLayouts()
	}
}

func (f *frontend) handleSettingsInput() {
	if f.selected == 0 && (rl.IsKeyPressed(rl.KeyLeft) || rl.IsKeyPressed(rl.KeyRight)) {
		layoutNames := []string{""}
		for _, layout := range f.layouts {
			layoutNames = append(layoutNames, strings.TrimSuffix(stringValue(layout["file_name"], ""), ".json"))
		}
		current := stringValue(f.settings["default_layout"], "")
		index := 0
		for i, name := range layoutNames {
			if name == current {
				index = i
			}
		}
		if rl.IsKeyPressed(rl.KeyLeft) {
			index = (index - 1 + len(layoutNames)) % len(layoutNames)
		} else {
			index = (index + 1) % len(layoutNames)
		}
		value := any(nil)
		if layoutNames[index] != "" {
			value = layoutNames[index]
		}
		if err := f.request(http.MethodPut, "/settings", map[string]any{"default_layout": value}, nil); err != nil {
			f.showStatus(err.Error())
		} else {
			f.settings["default_layout"] = value
			f.showStatus("Default layout updated")
		}
		f.loadSettings()
	}
	if f.selected == 1 && rl.IsKeyPressed(rl.KeyEnter) {
		value := !(f.settings["center_mouse_on_switch"] == true)
		if err := f.request(http.MethodPut, "/settings", map[string]any{"center_mouse_on_switch": value}, nil); err != nil {
			f.showStatus(err.Error())
		} else {
			f.settings["center_mouse_on_switch"] = value
			f.showStatus("Mouse centering updated")
		}
		f.loadSettings()
	}
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
	padding := clay.PaddingAll(20)
	if f.view == viewSwitcher && !f.textInput {
		padding.Top = 0
	}
	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("Root"),
		Layout: clay.LayoutConfig{
			LayoutDirection: clay.TOP_TO_BOTTOM,
			Sizing:          clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)},
			ChildAlignment:  clay.ChildAlignment{X: clay.ALIGN_X_LEFT, Y: clay.ALIGN_Y_TOP},
			Padding:         padding,
			ChildGap:        10,
		},
		BackgroundColor: background,
	}, func() {
		if f.textInput {
			text("Create New Layout", 24, primary)
			text("Layout name:", 18, muted)
			text(f.textValue+"_", 24, primary)
			text("Enter create | Esc cancel", 16, muted)
			return
		}
		if f.view != viewSwitcher {
			text(f.viewTitle, 24, primary)
			clay.UI()(clay.ElementDeclaration{Id: clay.ID("ViewList"), Layout: clay.LayoutConfig{LayoutDirection: clay.TOP_TO_BOTTOM, Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)}, ChildGap: 4}}, func() {
				for index, row := range f.viewRows {
					color := primary
					prefix := "  "
					if index == f.selected {
						color = selection
						prefix = "> "
					}
					text(prefix+row, 20, color)
				}
			})
			help := f.viewHelp
			if time.Now().Before(f.statusUntil) {
				help = f.status
			}
			text(help, 16, muted)
			return
		}

		if strings.HasPrefix(strings.TrimSpace(f.query), "/") {
			text("command: "+f.query, 24, primary)
			clay.UI()(clay.ElementDeclaration{Id: clay.ID("Commands"), Layout: clay.LayoutConfig{LayoutDirection: clay.TOP_TO_BOTTOM, Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)}, ChildGap: 4}}, func() {
				for index, entry := range f.filteredCommands() {
					color := primary
					prefix := "  "
					if index == f.selected {
						color = selection
						prefix = "> "
					}
					text(prefix+"/"+entry.name+" - "+entry.description, 20, color)
				}
			})
			text("Enter execute | Esc close", 16, muted)
			return
		}
		clay.UI()(clay.ElementDeclaration{Id: clay.ID("Header"), Layout: clay.LayoutConfig{Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingFixed(32)}}}, func() {
			text("query: "+f.query, 24, primary)
		})
		clay.UI()(clay.ElementDeclaration{Id: clay.ID("List"), Layout: clay.LayoutConfig{LayoutDirection: clay.TOP_TO_BOTTOM, Sizing: clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)}, ChildAlignment: clay.ChildAlignment{X: clay.ALIGN_X_LEFT, Y: clay.ALIGN_Y_TOP}, ChildGap: 4}}, func() {
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
		if f.keepOpen {
			help = "Enter to switch | Testing: window stays open | Ctrl+C in terminal to quit"
		}
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

func configureWindowPlatform() error {
	if runtime.GOOS != "linux" {
		return nil
	}
	if os.Getenv("WAYLAND_DISPLAY") == "" {
		return fmt.Errorf("BlinkSwitch Go frontend requires a Wayland session on Linux")
	}
	// Linux uses native Wayland even when an XWayland display is also available.
	return os.Unsetenv("DISPLAY")
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--toggle" {
		if notifyToggle() {
			return
		}
		os.Exit(1)
	}
	if err := configureWindowPlatform(); err != nil {
		fmt.Fprintf(os.Stderr, "Could not select window platform: %v\n", err)
		os.Exit(1)
	}
	rl.SetConfigFlags(rl.FlagWindowUndecorated | rl.FlagWindowTopmost | rl.FlagWindowResizable)
	rl.InitWindow(width, height, "BlinkSwitch Clay Frontend")
	defer rl.CloseWindow()
	// Escape toggles the switcher; it must not be Raylib's process exit key.
	rl.SetExitKey(0)
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
		client:   &http.Client{Timeout: 500 * time.Millisecond},
		mru:      map[string]int{},
		visible:  false,
		keepOpen: os.Getenv("BLINKSWITCH_KEEP_OPEN") == "1",
		toggle:   make(chan struct{}, 1),
	}
	f.fetch()
	if f.keepOpen {
		f.show()
	} else {
		startHotkeyListener(f.toggle)
		startIPCListener(f.toggle)
		f.hide()
	}
	renderCheck := os.Getenv("BLINKSWITCH_RENDER_CHECK") == "1"
	lastRenderReport := ""
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
		f.handleViewInput()
		for character := rl.GetCharPressed(); character > 0; character = rl.GetCharPressed() {
			if character >= 32 && character <= 126 {
				if f.textInput {
					f.textValue += string(rune(character))
				} else if f.view == viewSwitcher {
					f.query += string(rune(character))
					f.selected = 0
					f.filter()
				} else if f.view == viewAssign && character >= '1' && character <= '9' && f.selected < len(f.assignSlots) {
					monitorIndex := int(character - '1')
					if monitorIndex < len(f.monitors) {
						slotNumber := intValue(f.assignSlots[f.selected]["slot"])
						if slotNumber == 0 {
							slotNumber = f.selected + 1
						}
						f.assignment[fmt.Sprint(slotNumber)] = stringValue(f.monitors[monitorIndex]["identity_key"], "")
						f.rebuildAssignmentRows()
					}
				}
			}
		}
		if f.view == viewSwitcher && rl.IsKeyPressed(rl.KeyBackspace) && len(f.query) > 0 {
			f.query = f.query[:len(f.query)-1]
			f.selected = 0
			f.filter()
		}

		clay.SetLayoutDimensions(clay.Dimensions{Width: float32(rl.GetScreenWidth()), Height: float32(rl.GetScreenHeight())})
		clay.BeginLayout()
		f.draw()
		commands := clay.EndLayout()
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 50, G: 50, B: 50, A: 255})
		renderClay(commands)
		if renderCheck {
			report := probeRenderViewport()
			if report != lastRenderReport {
				fmt.Println(report)
				lastRenderReport = report
			}
			rl.DrawRectangleLinesEx(rl.Rectangle{Width: float32(rl.GetScreenWidth()), Height: float32(rl.GetScreenHeight())}, 2, rl.SkyBlue)
			mouse := rl.GetMousePosition()
			rl.DrawLine(int32(mouse.X)-8, int32(mouse.Y), int32(mouse.X)+8, int32(mouse.Y), rl.Yellow)
			rl.DrawLine(int32(mouse.X), int32(mouse.Y)-8, int32(mouse.X), int32(mouse.Y)+8, rl.Yellow)
		}
		rl.EndDrawing()
	}
}
