/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'

const security = require('../lib/insecurity')

// vuln-code-snippet start noSqlReviewsChallenge forgedReviewChallenge
module.exports = function productReviews () {
  return async (req: Request, res: Response, next: NextFunction) => {
    const user = security.authenticatedUsers.from(req)
    if (!user?.data?.email) {
      return res.status(401).json({ error: 'User not authenticated' })
    }

    if (!req.body.id || typeof req.body.id !== 'string' || !req.body.message || typeof req.body.message !== 'string') {
      return res.status(400).json({ error: 'Invalid input parameters' })
    }

    try {
      // First verify the review belongs to the user
      const review = await db.reviewsCollection.findOne({ _id: req.body.id, author: user.data.email })
      if (!review) {
        return res.status(403).json({ error: 'Access denied or review not found' })
      }

      // Update only the specific review owned by the user
      const result = await db.reviewsCollection.update(
        { _id: req.body.id, author: user.data.email },
        { $set: { message: req.body.message } }
      ).then(
      (result: { modified: number, original: Array<{ author: any }> }) => {
        challengeUtils.solveIf(challenges.noSqlReviewsChallenge, () => { return result.modified > 1 }) // vuln-code-snippet hide-line
        challengeUtils.solveIf(challenges.forgedReviewChallenge, () => { return user?.data && result.original[0] && result.original[0].author !== user.data.email && result.modified === 1 }) // vuln-code-snippet hide-line
        res.json(result)
      }, (err: unknown) => {
        res.status(500).json(err)
      })
  }
}
// vuln-code-snippet end noSqlReviewsChallenge forgedReviewChallenge
