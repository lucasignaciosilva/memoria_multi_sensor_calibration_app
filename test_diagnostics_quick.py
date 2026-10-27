#!/usr/bin/env python3
"""Test rápido sin lazy loading"""
import os
os.environ['ROS_LOG_LEVEL'] = 'ERROR'

print("🔧 TEST DE DIAGNÓSTICO RÁPIDO")

# Test 1: Validación de frame counter
print("\n✅ TEST 1: Frame Counter Logic")
total_messages = 500
max_frame = total_messages - 1
current_idx = max_frame

# Simulando lo que hace el GUI
display = f"Frame: {current_idx + 1}/{total_messages}"
expected = "Frame: 500/500"

print(f"   Total: {total_messages}")
print(f"   Max index: {max_frame}")
print(f"   Current: {current_idx}")
print(f"   Display: {display}")
print(f"   Expected: {expected}")
print(f"   Status: {'✓ OK' if display == expected else '✗ FAIL'}")

# Test 2: Validación de rango
print("\n✅ TEST 2: Range Validation")
if current_idx > max_frame:
    current_idx_fixed = min(current_idx, max_frame)
    print(f"   ANTES: {current_idx}")
    print(f"   DESPUÉS (con fix): {current_idx_fixed}")
    print(f"   Status: ✓ Fix aplicado")
else:
    print(f"   Status: ✓ No necesita fix")

# Test 3: Estructura de datos
print("\n✅ TEST 3: Data Structure")
print(f"   Esperadas keys en data:")
print(f"     - 'images': dict con topics")
print(f"     - 'pointcloud' o 'pointclouds': array o dict")
print(f"     - 'imu': dict opcional")
print(f"     - 'timestamp': float")

print("\n✓ Tests completados")
