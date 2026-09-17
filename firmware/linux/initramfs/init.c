/* BOOTX minimal userspace marker.
 *
 * This is PID 1 of a minimal initramfs -- not a real init system. Its only
 * job is to prove Linux handed off to userspace, by printing a marker the
 * BOOTX event parser looks for (bootx/tracing/parser.py, USERSPACE_READY),
 * then cleanly power off the VM via reboot(2) so QEMU exits on its own
 * instead of BOOTX having to rely on a timeout. On the QEMU virt platform
 * a poweroff request from the kernel is delivered to TF-A/EL3 as a real
 * PSCI SYSTEM_OFF call.
 */
#include <stdio.h>
#include <unistd.h>
#include <sys/reboot.h>

int main(void) {
    printf("BOOTX_USERSPACE_READY\n");
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    for (;;) {
    }
    return 0;
}
