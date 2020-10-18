#include <stdio.h>
#include <string.h>

#define __latent_entropy
#define __noinitretpoline
#define __cold          __attribute__((__cold__))
#define __section(S)    __attribute__((__section__(#S)))
#define __initdata      __section(.init.data)
#define __init          __section(.init.text) __cold  __latent_entropy __noinitretpoline


struct mpc_table {
	unsigned int reserved;
};

void probe_roms(void){}

void reserve_standard_io_resources(void){}

char *e820__memory_setup_default(void)
{
    char *ret = "";
    return ret;
}

void x86_init_uint_noop(unsigned int unused) { }

void __init default_smp_read_mpc_oem(struct mpc_table *mpc) { }

static int iommu_init_noop(void) { return 0; }

#define default_get_smp_config x86_init_uint_noop

struct x86_init_resources {
	void (*probe_roms)(void);
	void (*reserve_resources)(void);
	char *(*memory_setup)(void);
};

struct x86_init_mpparse {
	void (*mpc_record)(unsigned int mode);
	void (*smp_read_mpc_oem)(struct mpc_table *mpc);
	void (*get_smp_config)(unsigned int early);
};

struct x86_init_iommu {
	int (*iommu_init)(void);
};


struct x86_init_ops {
	struct x86_init_resources	resources;
	struct x86_init_mpparse		mpparse;
	struct x86_init_iommu		iommu;
};

struct x86_init_ops x86_init __initdata = {

	.resources = {
		.probe_roms		= probe_roms,
		.reserve_resources	= reserve_standard_io_resources,
		.memory_setup		= e820__memory_setup_default,
	},

	.mpparse = {
		.mpc_record		= x86_init_uint_noop,
		.smp_read_mpc_oem	= default_smp_read_mpc_oem,
        .get_smp_config		= default_get_smp_config,
	},

	.iommu = {
		.iommu_init		= iommu_init_noop,
	},
};

int main(void)
{
    struct mpc_table mpc;
    x86_init.mpparse.smp_read_mpc_oem(&mpc);
    x86_init.mpparse.get_smp_config(0);
}
