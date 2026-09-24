import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RecommendationCard from '../../src/components/RecommendationCard.vue'

const rec = {
  rec_id: 5,
  rank: 1,
  topic_title: 'Cloud Computing and Kubernetes',
  topic_description: 'Theme found in 20 passages.',
  composite_score: 0.834,
  ner_score: 0.9,
  topic_score: 0.8,
  novelty_score: 0.7,
  overlap_status: 'Potential Duplicate',
  planner_decision: null,
  planner_notes: null,
  evidence: { passages: [{ text: 'Deploy on Kubernetes.' }] },
}

const factory = (props) => mount(RecommendationCard, { props: { rec, ...props }, global: { stubs: { RouterLink: RouterLinkStub } } })

describe('RecommendationCard', () => {
  it('shows scores, statuses and evidence', () => {
    const wrapper = factory()
    expect(wrapper.text()).toContain('Cloud Computing and Kubernetes')
    expect(wrapper.text()).toContain('0.83')
    expect(wrapper.text()).toContain('Potential Duplicate')
    expect(wrapper.text()).toContain('Pending review')
    expect(wrapper.text()).toContain('Deploy on Kubernetes.')
    expect(wrapper.findAll('[role="progressbar"]')).toHaveLength(3)
  })

  it('hides decision controls from users who cannot review', () => {
    expect(factory({ canReview: false }).find('[data-test="accept"]').exists()).toBe(false)
  })

  it('emits decisions with notes and asks for justification on duplicates', async () => {
    const wrapper = factory({ canReview: true })
    const textarea = wrapper.find('textarea')
    expect(textarea.attributes('placeholder')).toContain('Justification required')
    await textarea.setValue('Applied practice beyond the core')
    await wrapper.find('[data-test="accept"]').trigger('click')
    expect(wrapper.emitted('decide')[0][0]).toMatchObject({ decision: 'Accepted', notes: 'Applied practice beyond the core' })
  })
})
