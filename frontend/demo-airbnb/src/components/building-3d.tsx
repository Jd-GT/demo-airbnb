"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

function WireframeBuilding() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.15;
    }
  });

  const goldMaterial = new THREE.LineBasicMaterial({ color: "#C9A227", transparent: true, opacity: 0.6 });
  const goldMaterialBright = new THREE.LineBasicMaterial({ color: "#E8D48B", transparent: true, opacity: 0.4 });

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
      <group ref={groupRef} scale={0.8}>
        {/* Main tower */}
        <lineSegments>
          <edgesGeometry args={[new THREE.BoxGeometry(1.2, 3, 1.2)]} />
          <lineBasicMaterial color="#C9A227" transparent opacity={0.6} />
        </lineSegments>

        {/* Second tower */}
        <lineSegments position={[1.8, -0.5, 0]}>
          <edgesGeometry args={[new THREE.BoxGeometry(1, 2, 1)]} />
          <lineBasicMaterial color="#C9A227" transparent opacity={0.4} />
        </lineSegments>

        {/* Small block */}
        <lineSegments position={[-1.5, -1, 0.3]}>
          <edgesGeometry args={[new THREE.BoxGeometry(0.8, 1, 0.8)]} />
          <lineBasicMaterial color="#E8D48B" transparent opacity={0.35} />
        </lineSegments>

        {/* Ground plane */}
        <lineSegments position={[0, -1.8, 0]} rotation={[0, 0, 0]}>
          <edgesGeometry args={[new THREE.PlaneGeometry(5, 4)]} />
          <lineBasicMaterial color="#C9A227" transparent opacity={0.15} />
        </lineSegments>

        {/* Floor lines on main tower */}
        {[...Array(6)].map((_, i) => (
          <lineSegments key={i} position={[0, -1.2 + i * 0.5, 0.601]}>
            <edgesGeometry args={[new THREE.PlaneGeometry(1.1, 0.01)]} />
            <lineBasicMaterial color="#C9A227" transparent opacity={0.2} />
          </lineSegments>
        ))}
      </group>
    </Float>
  );
}

export default function Building3D() {
  return (
    <div className="w-full h-full">
      <Canvas
        camera={{ position: [3, 2, 5], fov: 35 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={0.3} />
        <WireframeBuilding />
      </Canvas>
    </div>
  );
}
