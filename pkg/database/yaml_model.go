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

package database

import (
	"os"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"gopkg.in/yaml.v3"
)

const YamlModelPath = "db/model.yaml"

// LoadYamlModels 加载YAML模型配置
func (s *ModelStore) LoadYamlModels() ([]*Model, error) {
	data, err := os.ReadFile(YamlModelPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		gologger.Errorf("读取模型配置文件失败: %v", err)
		return nil, err
	}

	var models []*Model
	if err := yaml.Unmarshal(data, &models); err != nil {
		gologger.Errorf("解析模型配置文件失败: %v", err)
		return nil, err
	}

	return models, nil
}

// GetYamlModel 获取指定的YAML模型
func (s *ModelStore) GetYamlModel(modelID string) *Model {
	models, err := s.LoadYamlModels()
	if err != nil {
		return nil
	}
	for _, m := range models {
		if m.ModelID == modelID {
			return m
		}
	}
	return nil
}
