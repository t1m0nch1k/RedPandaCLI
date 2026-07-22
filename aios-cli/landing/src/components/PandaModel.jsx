import { useRef } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function PandaModel(props) {
  // Load the model
  const { scene } = useGLTF('/base_basic_pbr.glb');
  const groupRef = useRef();
  
  // Animate rotation based on scroll using native R3F hooks
  useFrame((state, delta) => {
    if (groupRef.current) {
      // Calculate scroll progress (0 to 1)
      const maxScroll = document.body.scrollHeight - window.innerHeight;
      const scrollProgress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
      
      // Target rotations
      const targetRotationY = scrollProgress * Math.PI; // Rotates 180 degrees over the full scroll
      const targetRotationX = scrollProgress * 0.3;     // Slight tilt up/down
      
      // Smoothly interpolate current rotation to target rotation using lerp
      groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, targetRotationY, 0.1);
      groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, targetRotationX, 0.1);
    }
  });

  return (
    <group ref={groupRef} {...props} dispose={null}>
      <primitive object={scene} />
    </group>
  );
}

useGLTF.preload('/base_basic_pbr.glb');
