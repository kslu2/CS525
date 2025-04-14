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
		meta.recirc_cnt = meta.recirc_cnt + 0x00000001;
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
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt8;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt9;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt10;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt11;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt12;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt13;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt14;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt15;

	action process_array_8() {
		// store value of the array at this stage
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt8.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_9() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt9.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_10() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt10.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_11() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt11.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_12() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt12.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_13() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt13.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_14() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt14.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	action process_array_15() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> curr_stage_val;
		vt15.read(curr_stage_val, (bit<32>) meta.vt_idx);

		hdr.netcache.value = (bit<NETCACHE_VALUE_WIDTH_MAX>) hdr.netcache.value << 64;
		hdr.netcache.value = hdr.netcache.value | (bit<NETCACHE_VALUE_WIDTH_MAX>) curr_stage_val;
	}

	table vtable_8 {
		key = {
			meta.vt_bitmap[7:7]: exact;
		}
		actions = {
			process_array_8;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_9 {
		key = {
			meta.vt_bitmap[6:6]: exact;
		}
		actions = {
			process_array_9;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_10 {
		key = {
			meta.vt_bitmap[5:5]: exact;
		}
		actions = {
			process_array_10;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_11 {
		key = {
			meta.vt_bitmap[4:4]: exact;
		}
		actions = {
			process_array_11;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_12 {
		key = {
			meta.vt_bitmap[3:3]: exact;
		}
		actions = {
			process_array_12;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_13 {
		key = {
			meta.vt_bitmap[2:2]: exact;
		}
		actions = {
			process_array_13;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_14 {
		key = {
			meta.vt_bitmap[1:1]: exact;
		}
		actions = {
			process_array_14;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_15 {
		key = {
			meta.vt_bitmap[0:0]: exact;
		}
		actions = {
			process_array_15;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
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

							vtable_8.apply(); vtable_9.apply(); vtable_10.apply(); vtable_11.apply();
							vtable_12.apply(); vtable_13.apply(); vtable_14.apply(); vtable_15.apply();
						}
						increment_recirculation();
						if (meta.recirc_cnt < RECIRCULATION_COUNT) {
							meta.temp_value = hdr.netcache.value;
							recirculate_preserving_field_list(1);
						}
					}
				}

				NoAction: {}
			}	
		}
	}
}
