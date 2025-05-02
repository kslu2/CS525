#include <core.p4>
#include <v1model.p4>

#include "../include/headers.p4"

#define CONTROLLER_MIRROR_SESSION 100
#define HOT_KEY_THRESHOLD 3

#define PKT_INSTANCE_TYPE_NORMAL 0
#define PKT_INSTANCE_TYPE_INGRESS_CLONE 1
#define PKT_INSTANCE_TYPE_EGRESS_CLONE 2
#define PKT_INSTANCE_TYPE_COALESCED 3
#define PKT_INSTANCE_TYPE_INGRESS_RECIRC 4
#define PKT_INSTANCE_TYPE_REPLICATION 5
#define PKT_INSTANCE_TYPE_RESUBMIT 6

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
	/* store metadata for a given key to find its values and index it properly */
	action egress_set_lookup_metadata(vtableBitmap_t vt_bitmap, vtableIdx_t vt_idx, keyIdx_t key_idx) {
		meta.vt_bitmap = vt_bitmap;
		meta.vt_idx = vt_idx;
		meta.key_idx = key_idx;
	}

	action increment_recirculation() {
		meta.recirc_cnt = meta.recirc_cnt + 0x00000002;
	}

	/* define cache lookup table */
	table egress_lookup_table {

		key = {
			hdr.netcache.key : exact;
		}

		actions = {
			egress_set_lookup_metadata;
			NoAction;
		}

		size = NETCACHE_ENTRIES * INGRESS_VTABLE_NUM;
		default_action = NoAction;

	}

	// register storing a bit to indicate whether an element in the cache
	// is valid or invalid
  	register<bit<1>>(NETCACHE_ENTRIES * EGRESS_VTABLE_NUM) egress_cache_status;

	// maintain 8 value tables since we need to spread them across stages
	// where part of the value is created from each stage (4.4.2 section)

	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt20;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt21;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt22;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt23;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt24;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt25;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt26;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt27;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt28;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt29;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt30;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt31;

	action process_array_20() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt20.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt20.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_21() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt21.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt21.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_22() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt22.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt22.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_23() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt23.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt23.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_24() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt24.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt24.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_25() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt25.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt25.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_26() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt26.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt26.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_27() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt27.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt27.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_28() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt28.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt28.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_29() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt29.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt29.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_30() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt30.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt30.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_31() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt31.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt31.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

    apply {
		if (hdr.netcache.isValid()) {
			switch(egress_lookup_table.apply().action_run)  {
				egress_set_lookup_metadata: {
					if (hdr.netcache.op == READ_QUERY) {
						bit<1> cache_valid_bit;

						egress_cache_status.read(cache_valid_bit, (bit<32>) meta.key_idx);
						meta.cache_valid = (cache_valid_bit == 1);

						if (meta.cache_valid) 
						{
							meta.vt_idx = meta.vt_idx + (bit<16>) meta.recirc_cnt;
							process_array_20(); process_array_21(); process_array_22(); process_array_23();
							process_array_24(); process_array_25(); process_array_26(); process_array_27();
							process_array_28(); process_array_29(); process_array_30(); process_array_31();
						}
						increment_recirculation();
						if (meta.recirc_cnt < RECIRCULATION_COUNT*2) {
							recirculate_preserving_field_list(1);
						}
					}
				}

				NoAction: {
					
				}
			}	
		}
	}
}
