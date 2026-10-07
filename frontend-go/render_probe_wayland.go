//go:build linux && wayland && cgo

package main

/*
typedef struct GLFWwindow GLFWwindow;
extern GLFWwindow *glfwGetCurrentContext(void);
extern void glfwGetFramebufferSize(GLFWwindow *window, int *width, int *height);
extern void (*glfwGetProcAddress(const char *name))(void);

static int readViewport(int *values) {
    typedef void (*GetIntegers)(unsigned int, int *);
    GetIntegers getIntegers = (GetIntegers)glfwGetProcAddress("glGetIntegerv");
    if (!getIntegers) return 0;
    getIntegers(0x0BA2, values); // GL_VIEWPORT
    return 1;
}
*/
import "C"

import (
	"fmt"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Called on the rendering thread with the default framebuffer active.
func probeRenderViewport() string {
	window := C.glfwGetCurrentContext()
	if window == nil {
		return "RENDER CHECK FAIL: no current GLFW context"
	}
	var framebufferWidth, framebufferHeight C.int
	C.glfwGetFramebufferSize(window, &framebufferWidth, &framebufferHeight)
	var viewport [4]C.int
	if C.readViewport(&viewport[0]) == 0 {
		return "RENDER CHECK FAIL: OpenGL viewport query unavailable"
	}
	status := "PASS"
	if framebufferWidth <= 0 || framebufferHeight <= 0 || viewport[0] != 0 || viewport[1] != 0 ||
		viewport[2] != framebufferWidth || viewport[3] != framebufferHeight {
		status = "FAIL"
	}
	dpi := rl.GetWindowScaleDPI()
	return fmt.Sprintf("RENDER CHECK %s: screen=%dx%d render=%dx%d framebuffer=%dx%d viewport=%d,%d,%d,%d dpi=%.2f,%.2f",
		status, rl.GetScreenWidth(), rl.GetScreenHeight(), rl.GetRenderWidth(), rl.GetRenderHeight(),
		int(framebufferWidth), int(framebufferHeight), int(viewport[0]), int(viewport[1]), int(viewport[2]), int(viewport[3]), dpi.X, dpi.Y)
}
