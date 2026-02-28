/*
File: DigitalTwin/pages/CameraManager.js
Description:
  Runtime camera mode manager for Digital Twin page, supporting FOLLOW/FREE and advanced view modes.
Usage:
  Import `createCameraManager(...)`, then call `update()` each frame and `setMode(...)` from UI/debug APIs.
Version: v1.2 (2026-02-27 20:43)
Revision History:
- 2026-02-27 20:43 v1.2 - Reduced FOLLOW/HORIZON target lag by increasing smoothing gain so camera stays tightly attached during stress-walk speed changes.
- 2026-02-27 20:36 v1.1 - Added FOLLOW/HORIZON follow-distance controls for wheel zoom behavior while preserving target lock and world-frame invariance.
- 2026-02-27 20:06 v1.0 - Added camera manager module with FOLLOW, FREE, FPV, HORIZON, and TOPDOWN modes.
*/

import * as THREE from 'three';

export function createCameraManager({ camera, controls, dogRoot, targetY = 0.74 }) {
  const _prevTarget = new THREE.Vector3();
  const _desiredTarget = new THREE.Vector3();
  const _desiredCamPos = new THREE.Vector3();
  const _fpvOffset = new THREE.Vector3(0.18, 0.30, 0.0);
  const _fpvLookAhead = new THREE.Vector3(0.58, 0.22, 0.0);
  const _tmpPos = new THREE.Vector3();
  const _tmpLook = new THREE.Vector3();

  const state = {
    mode: 'FOLLOW',
    targetY,
    smoothing: 0.16,
    followOffset: new THREE.Vector3(0.0, 0.58, 2.05),
    topDownHeight: 2.95,
    followDistanceMin: 0.95,
    followDistanceMax: 8.50,
  };

  const _followDir = new THREE.Vector3();

  function clampDistance(distance) {
    return THREE.MathUtils.clamp(
      Number(distance || 0),
      Number(state.followDistanceMin || 0.95),
      Number(state.followDistanceMax || 8.50),
    );
  }

  function setFollowDistance(distance) {
    const next = clampDistance(distance);
    if (state.followOffset.lengthSq() <= 1e-9) {
      state.followOffset.set(0.0, 0.30, next);
      return next;
    }
    _followDir.copy(state.followOffset).normalize().multiplyScalar(next);
    state.followOffset.copy(_followDir);
    return next;
  }

  function adjustFollowDistance(delta) {
    const mode = String(state.mode || '');
    if (mode !== 'FOLLOW' && mode !== 'HORIZON') return null;
    const current = state.followOffset.length();
    const next = setFollowDistance(current + Number(delta || 0));
    return next;
  }

  function normalizeMode(mode) {
    const m = String(mode || '').trim().toUpperCase();
    if (m === 'FREE' || m === 'FPV' || m === 'HORIZON' || m === 'TOPDOWN') return m;
    return 'FOLLOW';
  }

  function setMode(mode) {
    state.mode = normalizeMode(mode);
    controls.enabled = (state.mode === 'FREE');
    return state.mode;
  }

  function getState() {
    return {
      mode: state.mode,
      cameraPos: {
        x: Number(camera.position.x || 0),
        y: Number(camera.position.y || 0),
        z: Number(camera.position.z || 0),
      },
      target: {
        x: Number(controls.target.x || 0),
        y: Number(controls.target.y || 0),
        z: Number(controls.target.z || 0),
      },
    };
  }

  function update() {
    const baseX = Number(dogRoot.position.x || 0);
    const baseZ = Number(dogRoot.position.z || 0);
    const baseTargetY = Number(state.targetY || 0.74);

    if (state.mode === 'FREE') {
      controls.enabled = true;
      return;
    }

    controls.enabled = false;
    _prevTarget.copy(controls.target);
    _desiredTarget.set(baseX, baseTargetY, baseZ);

    if (state.mode === 'TOPDOWN') {
      controls.target.lerp(_desiredTarget, 0.18);
      _desiredCamPos.set(baseX, Number(state.topDownHeight || 2.95), baseZ + 0.001);
      camera.position.lerp(_desiredCamPos, 0.18);
      camera.lookAt(controls.target);
      return;
    }

    if (state.mode === 'FPV') {
      _tmpPos.copy(_fpvOffset);
      dogRoot.localToWorld(_tmpPos);
      _tmpLook.copy(_fpvLookAhead);
      dogRoot.localToWorld(_tmpLook);
      camera.position.lerp(_tmpPos, 0.22);
      controls.target.copy(_tmpLook);
      camera.lookAt(_tmpLook);
      return;
    }

    if (state.mode === 'HORIZON') {
      controls.target.lerp(_desiredTarget, state.smoothing);
      _desiredCamPos.copy(_desiredTarget).add(state.followOffset);
      camera.position.lerp(_desiredCamPos, state.smoothing);
      camera.up.set(0, 1, 0);
      camera.lookAt(controls.target);
      return;
    }

    controls.target.lerp(_desiredTarget, state.smoothing);
    _desiredCamPos.copy(_desiredTarget).add(state.followOffset);
    camera.position.lerp(_desiredCamPos, state.smoothing);
    camera.lookAt(controls.target);
  }

  return {
    setMode,
    getState,
    setFollowDistance,
    adjustFollowDistance,
    update,
  };
}
