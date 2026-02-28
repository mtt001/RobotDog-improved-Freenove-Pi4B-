/*
File: DigitalTwin/pages/ServoHierarchy.js
Description:
  Servo hierarchy helpers for Digital Twin leg-joint rotations and debug axis markers.
Usage:
  Import helpers to apply per-leg S11/S12/S13 rotations and attach axes to body/joints.
Version: v1.1 (2026-02-27 20:36)
Revision History:
- 2026-02-27 20:36 v1.1 - Corrected joint hinge mapping for current rig: S12/S13/ankle now drive local Z hinge axis so Servo Test motion matches visible leg geometry.
- 2026-02-27 20:06 v1.0 - Added reusable helpers for 3D servo hierarchy rotations and joint-axis debug visualization.
*/

export function applyLegJointRotations(THREE, leg, rotationDeg) {
  const rollRad = THREE.MathUtils.degToRad(Number(rotationDeg.rollDeg || 0));
  const pitchRad = THREE.MathUtils.degToRad(Number(rotationDeg.hipPitchDeg || 0));
  const kneeRad = THREE.MathUtils.degToRad(Number(rotationDeg.kneeDeg || 0));
  const ankleRad = THREE.MathUtils.degToRad(Number(rotationDeg.ankleDeg || 0));

  if (leg.hipPivot) {
    leg.hipPivot.rotation.x = rollRad;
    leg.hipPivot.rotation.y = 0;
    leg.hipPivot.rotation.z = 0;
  }
  if (leg.pitchPivot) {
    leg.pitchPivot.rotation.x = 0;
    leg.pitchPivot.rotation.y = 0;
    leg.pitchPivot.rotation.z = pitchRad;
  }
  if (leg.kneePivot) {
    leg.kneePivot.rotation.x = 0;
    leg.kneePivot.rotation.y = 0;
    leg.kneePivot.rotation.z = -kneeRad;
  }
  if (leg.anklePivot) {
    leg.anklePivot.rotation.x = 0;
    leg.anklePivot.rotation.y = 0;
    leg.anklePivot.rotation.z = ankleRad;
  }
}

export function attachServoAxesHelpers(THREE, bodyRoot, legRigs, axisLen = 0.095) {
  if (bodyRoot && !bodyRoot.userData?.bodyAxisHelperAttached) {
    const bodyAxis = new THREE.AxesHelper(axisLen * 1.35);
    bodyAxis.renderOrder = 210;
    bodyRoot.add(bodyAxis);
    if (!bodyRoot.userData) bodyRoot.userData = {};
    bodyRoot.userData.bodyAxisHelperAttached = true;
  }

  const frontRight = Array.isArray(legRigs)
    ? legRigs.find((leg) => String(leg.key) === 'front_right')
    : null;
  if (!frontRight) return;

  const attachOne = (parent, key) => {
    if (!parent) return;
    if (!parent.userData) parent.userData = {};
    const marker = `axisHelper_${key}`;
    if (parent.userData[marker]) return;
    const helper = new THREE.AxesHelper(axisLen);
    helper.renderOrder = 211;
    parent.add(helper);
    parent.userData[marker] = true;
  };

  attachOne(frontRight.hipPivot, 's11');
  attachOne(frontRight.pitchPivot, 's12');
  attachOne(frontRight.kneePivot, 's13');
}
