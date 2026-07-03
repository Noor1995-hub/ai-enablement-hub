// Aliases over the generated OpenAPI types so pages never spell out the
// components['schemas'][...] indexing. Grows as Batches 5–6 port more pages.
import type { components } from '../api/schema'

export type UserProfile = components['schemas']['UserProfileResponse']
export type TokenPair = components['schemas']['TokenPairResponse']
export type InviteInfo = components['schemas']['InviteInfoResponse']
