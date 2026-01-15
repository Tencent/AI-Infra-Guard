package database

import (
	"os"

	"gopkg.in/yaml.v3"
	"trpc.group/trpc-go/trpc-go/log"
)

const YamlModelPath = "db/model.yaml"

// LoadYamlModels 加载YAML模型配置
func (s *ModelStore) LoadYamlModels() ([]*Model, error) {
	data, err := os.ReadFile(YamlModelPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		log.Errorf("读取模型配置文件失败: %v", err)
		return nil, err
	}

	var models []*Model
	if err := yaml.Unmarshal(data, &models); err != nil {
		log.Errorf("解析模型配置文件失败: %v", err)
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
