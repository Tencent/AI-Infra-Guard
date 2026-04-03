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

// Package httpx 编码转换测试
package httpx

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/encoding/traditionalchinese"
	"golang.org/x/text/transform"
	"io/ioutil"
	"strings"
)

// encodeToGBK 将 UTF-8 字符串编码为 GBK 字节（测试辅助函数）
func encodeToGBK(s string) ([]byte, error) {
	encoder := simplifiedchinese.GBK.NewEncoder()
	reader := transform.NewReader(strings.NewReader(s), encoder)
	return ioutil.ReadAll(reader)
}

// encodeToBig5 将 UTF-8 字符串编码为 BIG5 字节（测试辅助函数）
func encodeToBig5(s string) ([]byte, error) {
	encoder := traditionalchinese.Big5.NewEncoder()
	reader := transform.NewReader(strings.NewReader(s), encoder)
	return ioutil.ReadAll(reader)
}

// TestDecodegbk_ChineseText 测试 GBK 中文转 UTF-8
func TestDecodegbk_ChineseText(t *testing.T) {
	original := "你好世界"
	// 先将 UTF-8 编码为 GBK
	gbkBytes, err := encodeToGBK(original)
	require.NoError(t, err, "编码为 GBK 不应出错")

	// 再解码回 UTF-8
	utf8Bytes, err := Decodegbk(gbkBytes)
	require.NoError(t, err, "GBK 解码不应出错")
	assert.Equal(t, original, string(utf8Bytes), "GBK 解码后应还原为原始中文字符串")
}

// TestDecodegbk_ASCII 测试纯 ASCII 字符 GBK 解码（ASCII 在 GBK 中兼容）
func TestDecodegbk_ASCII(t *testing.T) {
	input := []byte("Hello, World!")
	result, err := Decodegbk(input)
	require.NoError(t, err, "ASCII 输入的 GBK 解码不应出错")
	assert.Equal(t, "Hello, World!", string(result), "ASCII 字符应原样保留")
}

// TestDecodegbk_Empty 测试空字节切片 GBK 解码
func TestDecodegbk_Empty(t *testing.T) {
	result, err := Decodegbk([]byte{})
	require.NoError(t, err, "空输入解码不应出错")
	assert.Equal(t, []byte{}, result, "空输入应返回空结果")
}

// TestDecodebig5_ChineseText 测试 BIG5 繁体中文转 UTF-8
func TestDecodebig5_ChineseText(t *testing.T) {
	original := "繁體中文測試"
	// 先将 UTF-8 编码为 BIG5
	big5Bytes, err := encodeToBig5(original)
	require.NoError(t, err, "编码为 BIG5 不应出错")

	// 再解码回 UTF-8
	utf8Bytes, err := Decodebig5(big5Bytes)
	require.NoError(t, err, "BIG5 解码不应出错")
	assert.Equal(t, original, string(utf8Bytes), "BIG5 解码后应还原为原始繁体中文字符串")
}

// TestDecodebig5_ASCII 测试纯 ASCII 字符 BIG5 解码
func TestDecodebig5_ASCII(t *testing.T) {
	input := []byte("Test123")
	result, err := Decodebig5(input)
	require.NoError(t, err, "ASCII 输入的 BIG5 解码不应出错")
	assert.Equal(t, "Test123", string(result), "ASCII 字符应原样保留")
}

// TestDecodebig5_Empty 测试空字节切片 BIG5 解码
func TestDecodebig5_Empty(t *testing.T) {
	result, err := Decodebig5([]byte{})
	require.NoError(t, err, "空输入解码不应出错")
	assert.Equal(t, []byte{}, result, "空输入应返回空结果")
}

// TestDecodegbk_RoundTrip 测试 GBK 编解码往返一致性
func TestDecodegbk_RoundTrip(t *testing.T) {
	samples := []string{
		"腾讯安全",
		"AI-Infra-Guard",
		"朱雀实验室",
	}
	for _, s := range samples {
		gbkBytes, err := encodeToGBK(s)
		require.NoError(t, err)
		decoded, err := Decodegbk(gbkBytes)
		require.NoError(t, err)
		assert.Equal(t, s, string(decoded), "GBK 往返转换应还原原始字符串: %q", s)
	}
}

// TestDecodebig5_RoundTrip 测试 BIG5 编解码往返一致性
func TestDecodebig5_RoundTrip(t *testing.T) {
	samples := []string{
		"繁體字測試",
		"台灣繁體中文",
	}
	for _, s := range samples {
		big5Bytes, err := encodeToBig5(s)
		require.NoError(t, err)
		decoded, err := Decodebig5(big5Bytes)
		require.NoError(t, err)
		assert.Equal(t, s, string(decoded), "BIG5 往返转换应还原原始字符串: %q", s)
	}
}
