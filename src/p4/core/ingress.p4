#include <core.p4>
#include <v1model.p4>

#include "../include/headers.p4"

#define CONTROLLER_MIRROR_SESSION 100

#define pkt_instance_type_normal 0
#define pkt_instance_type_ingress_clone 1
#define pkt_instance_type_egress_clone 2
#define pkt_instance_type_coalesced 3
#define pkt_instance_type_ingress_recirc 4
#define pkt_instance_type_replication 5
#define pkt_instance_type_resubmit 6
#define RECIRCULATION_PORT 2

#define pkt_is_not_mirrored \
	 ((standard_metadata.instance_type == pkt_instance_type_normal) || \
	  (standard_metadata.instance_type == pkt_instance_type_replication))


control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {


	action drop() {
		mark_to_drop(standard_metadata);
	}

	action set_egress_port(egressSpec_t port) {
		standard_metadata.egress_spec = port;
	}

	/* Simple l2 forwarding logic */
	table l2_forward {

		key = {
			hdr.ethernet.dstAddr: exact;
		}

		actions = {
			set_egress_port;
			drop;
		}

		size = 1024;
		default_action = drop();

	}

	action set_egress_port_recirculation() {
		standard_metadata.egress_spec = RECIRCULATION_PORT;
	}



	 /* update the packet header by swapping the source and destination addresses
	  * and ports in L2-L4 header fields in order to make the packet ready to
	  * return to the sender (tcp is more subtle than just swapping addresses) */
	action ret_pkt_to_sender() {

		macAddr_t macTmp;
		macTmp = hdr.ethernet.srcAddr;
		hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
		hdr.ethernet.dstAddr = macTmp;

		ip4Addr_t ipTmp;
		ipTmp = hdr.ipv4.srcAddr;
		hdr.ipv4.srcAddr = hdr.ipv4.dstAddr;
		hdr.ipv4.dstAddr = ipTmp;

		bit<16> portTmp;
		if (hdr.udp.isValid()) {
			portTmp = hdr.udp.srcPort;
			hdr.udp.srcPort = hdr.udp.dstPort;
			hdr.udp.dstPort = portTmp;
		} else if (hdr.tcp.isValid()) {
			portTmp = hdr.tcp.srcPort;
			hdr.tcp.srcPort = hdr.tcp.dstPort;
			hdr.tcp.dstPort = portTmp;
		}

	}


	/* store metadata for a given key to find its values and index it properly */
	action ingress_set_lookup_metadata(vtableBitmap_t vt_bitmap, vtableIdx_t vt_idx, keyIdx_t key_idx) {
		meta.vt_bitmap = vt_bitmap;
		meta.vt_idx = vt_idx;
		meta.key_idx = key_idx;
	}

	/* define cache lookup table */
	table ingress_lookup_table {

		key = {
			hdr.netcache.key : exact;
		}

		actions = {
			ingress_set_lookup_metadata;
			NoAction;
		}

		size = NETCACHE_ENTRIES * INGRESS_VTABLE_NUM;
		default_action = NoAction;

	}


    // register storing a bit to indicate whether an element in the cache
    // is valid or invalid
    register<bit<1>>(NETCACHE_ENTRIES * INGRESS_VTABLE_NUM) ingress_cache_status;

	// maintain 8 value tables since we need to spread them across stages
	// where part of the value is created from each stage (4.4.2 section)
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt0;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt1;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt2;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt3;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt4;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt5;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt6;
	register<bit<NETCACHE_VTABLE_SLOT_WIDTH>>(NETCACHE_ENTRIES) vt7;

	action process_array_0() {
		// store value of the array at this stage
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt0.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt0.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt0.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}	
	}


	action process_array_1() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt1.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt1.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt1.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_2() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt2.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt2.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt2.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_3() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt3.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt3.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt3.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_4() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt4.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt4.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt4.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_5() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt5.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt5.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt5.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_6() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt6.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt6.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt6.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}

	action process_array_7() {
		bit<NETCACHE_VTABLE_SLOT_WIDTH> val;
		vt7.read(val, (bit<32>) meta.vt_idx);
		if (meta.recirc_cnt < 0x00000002) {
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt7.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value = (hdr.netcache.value << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		} else {
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;

			vt7.read(val, (bit<32>) meta.vt_idx + 1);
			hdr.netcache.value2 = (hdr.netcache.value2 << NETCACHE_VTABLE_SLOT_WIDTH) | (bit<NETCACHE_VALUE_WIDTH_MAX>) val;
		}
	}


	table vtable_0 {
		key = {
			meta.vt_bitmap[7:7]: exact;
		}
		actions = {
			process_array_0;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_1 {
		key = {
			meta.vt_bitmap[6:6]: exact;
		}
		actions = {
			process_array_1;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_2 {
		key = {
			meta.vt_bitmap[5:5]: exact;
		}
		actions = {
			process_array_2;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_3 {
		key = {
			meta.vt_bitmap[4:4]: exact;
		}
		actions = {
			process_array_3;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_4 {
		key = {
			meta.vt_bitmap[3:3]: exact;
		}
		actions = {
			process_array_4;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_5 {
		key = {
			meta.vt_bitmap[2:2]: exact;
		}
		actions = {
			process_array_5;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_6 {
		key = {
			meta.vt_bitmap[1:1]: exact;
		}
		actions = {
			process_array_6;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}

	table vtable_7 {
		key = {
			meta.vt_bitmap[0:0]: exact;
		}
		actions = {
			process_array_7;
			NoAction;
		}
		size = NETCACHE_ENTRIES;
		default_action = NoAction;
	}



	apply {

		if (hdr.netcache.isValid()) {


            switch(ingress_lookup_table.apply().action_run) {

				ingress_set_lookup_metadata: {

                    if (hdr.netcache.op == READ_QUERY){

						bit<1> cache_valid_bit;
						ingress_cache_status.read(cache_valid_bit, (bit<32>) meta.key_idx);

						// read query should be answered by switch if the key
						// resides in cache and its entry is valid
						meta.cache_valid = (cache_valid_bit == 1);


						if (meta.cache_valid && hdr.udp.srcPort != NETCACHE_PORT) {
							meta.vt_idx = meta.vt_idx + (bit<16>) meta.recirc_cnt;
							vtable_0.apply(); vtable_1.apply(); vtable_2.apply(); vtable_3.apply();
							vtable_4.apply(); vtable_5.apply(); vtable_6.apply(); vtable_7.apply();
						}

						if (meta.recirc_cnt < (RECIRCULATION_COUNT - 1)*2) {
							standard_metadata.instance_type = pkt_instance_type_ingress_recirc;
							set_egress_port_recirculation();
						} else {
							standard_metadata.instance_type = pkt_instance_type_normal;
							ret_pkt_to_sender();
						}
                    }
				}
				NoAction: {
					if (hdr.netcache.op == WRITE_QUERY) {
						if (pkt_is_not_mirrored) {
							clone(CloneType.I2E, CONTROLLER_MIRROR_SESSION);
							ret_pkt_to_sender();
						}
					} else if (hdr.netcache.op == READ_QUERY) {
						hdr.netcache.op = READ_FAIL;
					} else if (hdr.netcache.op == FLUSH_QUERY) {
						if (pkt_is_not_mirrored) {
							clone(CloneType.I2E, CONTROLLER_MIRROR_SESSION);
							ret_pkt_to_sender();
						}
					}
				}
            }
        }
		if (standard_metadata.egress_spec != RECIRCULATION_PORT) {
			l2_forward.apply();
		}
	}

}
