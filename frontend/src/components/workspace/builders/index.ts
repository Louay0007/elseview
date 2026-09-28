import type { ComponentType } from "react";
import type { BuilderProps } from "./types";
import { PrototypeBuilder } from "./PrototypeBuilder";
import { CardSortBuilder } from "./CardSortBuilder";
import { TreeTestBuilder } from "./TreeTestBuilder";
import { PreferenceBuilder } from "./PreferenceBuilder";
import { FirstClickBuilder, FiveSecondBuilder } from "./ExposureBuilders";
import { SurveyBuilder } from "./SurveyBuilder";
import { AccessibilityBuilder, LanguageBuilder, MediaBuilder } from "./ReviewBuilders";

export type BuilderComponent = ComponentType<BuilderProps>;

const REGISTRY: Record<string, BuilderComponent> = {
  "prototype.task": PrototypeBuilder,
  card_sort: CardSortBuilder,
  tree_test: TreeTestBuilder,
  preference: PreferenceBuilder,
  five_second: FiveSecondBuilder,
  first_click: FirstClickBuilder,
  "survey.single": SurveyBuilder,
  "survey.multi": SurveyBuilder,
  "survey.rating": SurveyBuilder,
  "survey.text": SurveyBuilder,
  "survey.ranking": SurveyBuilder,
  "survey.constant_sum": SurveyBuilder,
  "accessibility.issue": AccessibilityBuilder,
  "language.review": LanguageBuilder,
  "media.review": MediaBuilder,
};

export function builderFor(method: string): BuilderComponent {
  return REGISTRY[method] ?? SurveyBuilder;
}

export function hasCustomBuilder(method: string) {
  return method in REGISTRY;
}
