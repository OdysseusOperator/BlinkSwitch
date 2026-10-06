# Performance Improvement Opportunities

This document tracks potential performance optimizations that could be implemented if performance becomes an issue.

## Collision Detection

### Current Implementation: 2-Tier Collision (Calculate On-Demand)

**Tier 1**: Bounding circle check (fast)
**Tier 2**: Project all vertices → convex hull → point-in-polygon (medium)

### Future Optimization #1: Backface Culling for Projection

**Current**: Project all vertices, then calculate convex hull
**Improvement**: Only project triangles facing upward (Y-normal > 0)

**Expected Gains**:
- Reduces vertices to project by 30-50%
- Faster convex hull calculation (fewer points)
- More accurate collision shape (no hidden vertices)

**Complexity**: Medium
- Need to store triangle face definitions per shape
- Calculate face normals after rotation
- Track which triangles are visible

**Estimated Performance**: 20-30% faster Tier 2 checks

**When to implement**: If asteroid count > 50 or frame time > 16ms

---

### Future Optimization #2: Per-Frame Polygon Caching

**Current**: Recalculate projected polygon for every bullet collision check
**Improvement**: Cache projected polygon per asteroid per frame

**Implementation**:
```go
type Asteroid struct {
    // ... existing fields ...
    cachedPolygon       []Vector2
    cachedRotationX/Y/Z float32
    cacheValid          bool
}

func (a *Asteroid) GetProjectedPolygon() []Vector2 {
    if !a.cacheValid || a.rotationChanged() {
        a.cachedPolygon = calculateProjection(...)
        a.cacheValid = true
    }
    return a.cachedPolygon
}
```

**Expected Gains**:
- Calculate projection once per frame instead of per bullet
- With 10 asteroids × 5 bullets: 5x reduction in projection calculations

**Complexity**: Low-Medium
- Add cache fields to Asteroid struct
- Invalidate cache when rotation changes
- Clear cache flag each frame

**Estimated Performance**: 3-5x faster in high bullet-count scenarios

**When to implement**: If bullet count > 20 simultaneously

---

### Future Optimization #3: Spatial Partitioning (Grid/Quadtree)

**Current**: Check every bullet against every asteroid (O(n×m))
**Improvement**: Divide world into grid cells, only check nearby asteroids

**Expected Gains**:
- Reduce collision checks by 70-90%
- Scales better with high entity counts

**Complexity**: High
- Implement spatial grid structure
- Update entity positions in grid each frame
- Query nearby cells for collision candidates

**Estimated Performance**: 5-10x faster with 50+ asteroids

**When to implement**: If asteroid count regularly exceeds 30-40

---

### Future Optimization #4: SIMD Vectorization

**Current**: Scalar math for vertex rotation/projection
**Improvement**: Use SIMD instructions to process 4 vertices at once

**Expected Gains**: 2-4x faster vertex transformations

**Complexity**: Very High (assembly or intrinsics)

**When to implement**: Last resort, only if frame budget critical

---

## Rendering

### Future Optimization #5: Frustum Culling for 3D Asteroids

**Current**: Render all asteroids, Raylib handles culling
**Improvement**: Pre-cull asteroids outside camera view before 3D mode

**Expected Gains**: 20-40% faster rendering with many off-screen asteroids

**Complexity**: Medium (implement frustum calculation)

**When to implement**: If asteroid count > 100 or rendering > 8ms

---

## Memory

### Future Optimization #6: Object Pooling

**Current**: Create/destroy bullets and asteroid fragments via GC
**Improvement**: Pre-allocate pools, reuse objects

**Expected Gains**:
- Reduce GC pauses
- More consistent frame times

**Complexity**: Medium

**When to implement**: If GC pauses noticeable (>1ms)

---

## Measurement Guidelines

Before implementing any optimization:

1. **Profile first**: Measure actual bottleneck with Go profiler
2. **Set target**: Define acceptable frame time budget (e.g., < 12ms for 60fps with 4ms headroom)
3. **Measure improvement**: Quantify actual gains vs complexity cost
4. **Regression test**: Ensure optimization doesn't break collision accuracy

**Current Status**: ✅ No optimizations needed yet - baseline performance acceptable
