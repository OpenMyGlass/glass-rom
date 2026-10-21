# XE24 vendor binaries

Proprietary files that the build extracts from the owner's XE24 factory image (`glass_1-img-5585826`, SHA-256 `76a9d3822077e993bba62c586e5e7cbb1217a81171d78033ff7c06ba285f2363`). This page holds facts only (path, size, SHA-256, short notes). The files themselves are never committed. It was produced offline:

```sh
tools/fetch-factory.sh factory/
tools/sparse.py factory/system.img factory/system.raw
tools/extract_vendor.py factory/system.raw ../android_device_glass_glass-1/proprietary-files.txt /tmp/vendor-check
```

The run wrote 36 files plus `device-vendor.mk`, exit 0, and reported no missing path. Sizes are in bytes.

Notes:
- `ducati-m3-core0-2gb.xem3` is XE-C only; `ducati-m3-core0.xem3` is the other variant.
- The PowerVR SGX540 files are the user-space half of IMG DDK 1.9 (see below).

## PowerVR DDK version

Phase R2 compares these with the OMAP4-AOSP `pvr-source`.

- Stock kernel module `/system/lib/modules/pvrsrvkm_sgx540_120.ko` (3647097 bytes, SHA-256 `a4a60b4e3cfd4ff010e9c3300abf484171e5f291b3b7b5fd695f74e3b3e58afc`): `SGX_DDK_Android sgxddk 19 1.9@2166536`. The ROM does not need it, so the list does not extract it. glass-kernel builds the module from the same DDK (`1.9@2166536`, MIT/GPL-2.0) for each of its kernels, and the stock module does not load into the `tuned` and `tuned-stable` kernels (90 CRCs of the symbols it imports differ). The device tree builds it from that DDK, and `tools/make_insecure_boot.py --pvr-module` puts glass-kernel's copy into test boot images.
- Its `vermagic`: `3.4.94-01990-g1cee760235d SMP preempt mod_unload modversions ARMv7 p2v8`.
- Its build path names `eurasia_km/eurasiacon/binary2_540_120_omap4430_android_release` under `ti_gfx/img-ddk-linux-android`.
- `libsrv_um_SGX540_120.so`: no version string (no `SGX DDK`, `@(#)` or `1.9@` match); it only carries the error names `PVRSRV_ERROR_BUILD_MISMATCH` and `PVRSRV_ERROR_DDK_VERSION_MISMATCH`.
- `libIMGegl_SGX540_120.so`: `1.4 build 1.9@2166536`.
- `libGLESv2_POWERVR_SGX540_120.so`: `OpenGL ES 2.0 build 1.9@2166536` and `OpenGL ES GLSL ES 1.00 build 1.9@2166536`.

36 files:

| Path | Size | SHA-256 | Note |
|---|---:|---|---|
| `/system/bin/bqflash` | 100280 | `86220654fbb53b339e03c8e4fe140c82565263f7d66dcf1ed2937d787e25cbab` |  |
| `/system/bin/raft` | 5336 | `6484acc8af7af37da4d6e03041f5d03cfbffc2012f000aaf0849ce6a231ebdc3` |  |
| `/system/bin/shm_service` | 25868 | `92887fb9915506adb87e36180581207eb7eda2fc31f5e29c3596ddd031adb1f8` |  |
| `/system/bin/sysproxy` | 50504 | `9ba96740cc5970c3dd6c2602f79b70fa4e3b010fb39ee45228207871caaa4e4a` |  |
| `/system/bin/sysproxyd` | 21832 | `0486df87f3a4fb4b88b099d66b7332eda4f0f874ee6f48960a56060a801c7700` |  |
| `/system/etc/audio_policy.conf` | 2422 | `feb0e1656c66c39f2c18e37acf6852226a71499ebe47532e17aa69f2f09180e7` |  |
| `/system/etc/wifi/bcmdhd.cal` | 919 | `435e4ab26aa159525f519671fa1a391595ea8fcaa6bd952fceaf0aeb697d2951` |  |
| `/system/lib/hw/audio.primary.glass_1.so` | 18712 | `88dca0e3dbf948b5b80c227a9599b7502806e5f6d5d902773c0a8aa8b49d22fc` |  |
| `/system/lib/hw/gps.omap4.so` | 1217632 | `3f68b133545f88a787ab73ae1cd466d9cbd451eed963789254189aeaba5ca493` |  |
| `/system/lib/hw/sensors.glass_1.so` | 5360 | `e1d0c82adb7ced75ae3a393fb503a63b42be7b6b42a8318b63daf9da965a0794` |  |
| `/system/vendor/bin/pvrsrvctl_SGX540_120` | 9328 | `a67fb9a952b5dd9e95a5b5ee04454964c39ba0eb948d8a753494f345556aff55` |  |
| `/system/vendor/bin/pvrsrvinit` | 9328 | `866377b83429d9dafc85e20403dd80ecdb9eb7569ba534532803fbbb5a53f106` |  |
| `/system/vendor/firmware/NVM2` | 18060 | `41211a7cb452522adc8494c7184acd18157ab4ee54fe285733f516c2b5f6866f` |  |
| `/system/vendor/firmware/bcm4330.hcd` | 56736 | `f87a3fc4c946da97d87a72915c0fcdf3594a3ccfc0751636a0ff75a90e7daf38` |  |
| `/system/vendor/firmware/ducati-m3-core0-2gb.xem3` | 6344279 | `fd5edc30d490b665c59daa87d67f4b12dfd9ea66aebdedeeba2310e4626a7ff4` | XE-C only |
| `/system/vendor/firmware/ducati-m3-core0.xem3` | 6344271 | `2c5e9e9853cd916dea3551d9a60933660dd7a02c55decf443ea94d68e98bb970` |  |
| `/system/vendor/firmware/fw_bcmdhd.bin` | 207496 | `c3f7c26a04b348431a4c1f569a013d516612977821d4a36d2416fe218d30c147` |  |
| `/system/vendor/firmware/glasshub.s19` | 15106 | `e718915abf377bd526889921d710253540bf2553e3ab2b609e0de7764cce9441` |  |
| `/system/vendor/firmware/tesla-dsp.xe64T` | 978654 | `4c34bb487a78fad2e43b3ed0c699f7a14ea1ed67c1d846103c105a4bd9f4afa7` |  |
| `/system/vendor/lib/egl/libEGL_POWERVR_SGX540_120.so` | 9152 | `a51731ebe69d476e2cf58d211809168242b167a79f4541eaa4c4e5647e662761` |  |
| `/system/vendor/lib/egl/libGLESv1_CM_POWERVR_SGX540_120.so` | 414924 | `5ebb2816a76db2db499318789a5885855bcc100cf501b2f4d276294f496ff4da` |  |
| `/system/vendor/lib/egl/libGLESv2_POWERVR_SGX540_120.so` | 357584 | `b3dbdad37db1c56bc0c81a6c89b217cd6e61be8e2816c518ecac38eb644f6242` |  |
| `/system/vendor/lib/hw/gralloc.omap4430.so` | 26676 | `8555d167839099507d9c551f5a11678ddbfa6e88493305c911e741febad8bb70` |  |
| `/system/vendor/lib/libIMGegl_SGX540_120.so` | 62660 | `20b369de22728726c73485b120293ed1004ac823d1bf6e454d284303c0aae568` |  |
| `/system/vendor/lib/libPVRScopeServices_SGX540_120.so` | 9204 | `9cb786c37d95967211a52e2dfa96d6d64d4ef2f82e7c9766e4739cdc39f170f7` |  |
| `/system/vendor/lib/libbltsville_gc2d.2.2.2.0.so` | 34644 | `06f1c5050b97e855c7ce840050391977495c91dd7b48376475829599cef38200` |  |
| `/system/vendor/lib/libbltsville_ticpu.2.1.0.0.so` | 162310 | `3d02c453f357c139280bd63118dd1be436d331fd74ee3e98d828df9dee557279` |  |
| `/system/vendor/lib/libbltsville_ticpu_license.txt` | 10593 | `04a18143e9ec89973b9c43ce494d4ea55e9b1a44e8a3db26ba3e0bce69d8297c` |  |
| `/system/vendor/lib/libglslcompiler_SGX540_120.so` | 259164 | `0d46d3affc203d2a66e47893d4c4bd81bc9a1e52220609d847edddd80d7af9e2` |  |
| `/system/vendor/lib/libpvr2d_SGX540_120.so` | 21480 | `887ff372b3aff90f2bd5e9aa582ad739bddaba348c38a524963ff1f69f148b41` |  |
| `/system/vendor/lib/libpvrANDROID_WSEGL_SGX540_120.so` | 9352 | `5c5360fc38cc0d94b63d02ae5b45c8c999ac88489e5716c0256335f337e314de` |  |
| `/system/vendor/lib/libsrv_init_SGX540_120.so` | 111596 | `58e14d7174dc5359acfb2b51a8e5e722a1be5c4259e815ac3f5e60876e7355ea` |  |
| `/system/vendor/lib/libsrv_um_SGX540_120.so` | 160856 | `9056069f6613e81fecff94ec94bb78c1b52a6b73ca8379eccf014cbfddf3a63d` |  |
| `/system/vendor/lib/libusc_SGX540_120.so` | 861320 | `f922aeb5f5644a16396b7c648a00836a1f17e71e0766b782f3c545d52dd3a2c6` |  |
| `/system/xbin/bootconfig` | 100260 | `973bc171f65b06221c0ee112b39aab429ad75868606e4d2b285a516d11d284de` |  |
| `/system/xbin/hex2bin` | 5388 | `3773c960e8d346d5c25e30c7b6bc7f572d358fd9ac5f93e905dafa49f5ad1bc0` |  |
