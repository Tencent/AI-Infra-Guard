// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

package runner

import (
	"strings"
	"testing"
)

// TestIPAddressesIPv6RangeDoesNotEmitIPv4: IPAddressesIPnet used
// binary.BigEndian.Uint32 on a 16-byte IPv6 mask/address, which reads only the
// first four bytes. A /32 IPv6 range silently became the unrelated IPv4
// 32.1.13.184. It must now report an error instead.
func TestIPAddressesIPv6RangeDoesNotEmitIPv4(t *testing.T) {
	ips, err := IPAddresses("2001:db8::/32")
	if err == nil {
		t.Fatalf("expected an error for an unsupported IPv6 range, got %v", ips)
	}
	for _, ip := range ips {
		if strings.Contains(ip, ".") {
			t.Fatalf("IPv6 CIDR produced a bogus IPv4 address: %s", ip)
		}
	}
}

// TestIPAddressesIPv6SingleHost: a single IPv6 host (/128) is a legitimate
// target and should be returned verbatim.
func TestIPAddressesIPv6SingleHost(t *testing.T) {
	ips, err := IPAddresses("2001:db8::1/128")
	if err != nil {
		t.Fatalf("single IPv6 host should be supported: %v", err)
	}
	if len(ips) != 1 || ips[0] != "2001:db8::1" {
		t.Fatalf("unexpected single-host result: %v", ips)
	}
}
